import email

import pytest

import auto_scan
from backend.adapters.mail_provider import MailProviderAdapter


class FakeImap:
    capabilities = ("MOVE",)

    def __init__(self, uid="42", message_id="<msg@example.test>"):
        self.uid_value = uid
        self.message_id = message_id
        self.folder = "INBOX"
        self.uidvalidity = {"INBOX": "7", "[Gmail]/Spam": "8"}
        self.moves = []
        self.refuse_move = False

    def select(self, folder, readonly=False):
        self.folder = folder
        return "OK", [b"1"]

    def response(self, name):
        return "UIDVALIDITY", [self.uidvalidity[self.folder].encode()]

    def uid(self, command, uid, *args):
        if command == "FETCH":
            raw = f"Message-ID: {self.message_id}\r\n\r\n".encode()
            return "OK", [(b"* 1 FETCH (UID 42 BODY[]", raw)]
        if command == "SEARCH":
            return "OK", [self.uid_value.encode()]
        if command == "MOVE":
            if self.refuse_move:
                return "NO", [b"refused"]
            self.moves.append((str(uid), args[0]))
            return "OK", [b"moved"]
        if command == "COPY":
            return "OK", [b"copied"]
        if command == "STORE":
            return "OK", [b"stored"]
        raise AssertionError(command)

    def expunge(self):
        return "OK", [b"expunged"]

    def close(self):
        pass

    def logout(self):
        pass


@pytest.fixture
def stored_email():
    return {
        "id": "doc-1",
        "message_id": "<msg@example.test>",
        "imap_uid": "42",
        "mailbox_account_id": "account-id",
        "source_folder": "INBOX",
        "source_uidvalidity": "7",
        "provider": "Gmail",
        "folder": "inbox",
        "mailbox_action": "none",
        "subject": "Test job",
        "sender": "recruiter@example.test",
    }


def patch_db(monkeypatch, stored_email):
    saved = []
    monkeypatch.setattr(auto_scan, "mailbox_account_id", lambda credentials: "account-id")
    monkeypatch.setattr(auto_scan, "db_fetch_email", lambda doc_id, user_id: stored_email)
    monkeypatch.setattr(auto_scan, "db_update_email_fields", lambda doc_id, fields, user_id: saved.append(fields) or {**stored_email, **fields})
    monkeypatch.setattr(auto_scan, "db_write_audit", lambda **kwargs: {})
    return saved


def test_move_uses_session_credentials_and_confirms_spam(monkeypatch, stored_email):
    saved = patch_db(monkeypatch, stored_email)
    fake = FakeImap()
    credentials = {
        "provider": "Gmail", "username": "session@gmail.com", "password": "session-token",
        "server": "imap.gmail.com", "port": 993,
    }
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: credentials)
    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: fake)
    monkeypatch.setattr(auto_scan, "close_imap", lambda mail: None)

    result = MailProviderAdapter.move_to_spam("doc-1", "test", "visitor-1")

    assert result == {"ok": True, "mailbox_moved": True, "local_quarantined": True, "error": None}
    assert fake.moves == [("42", '"[Gmail]/Spam"')]
    assert saved[-1]["mailbox_action"] == "moved_to_spam"
    assert saved[-1]["provider_folder"] == "[Gmail]/Spam"


def test_no_session_credentials_is_local_only(monkeypatch, stored_email):
    saved = patch_db(monkeypatch, stored_email)
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: None)

    result = MailProviderAdapter.move_to_spam("doc-1", "test", "visitor-1")

    assert result["ok"] is True
    assert result["mailbox_moved"] is False
    assert result["local_quarantined"] is True
    assert "SafeApply only" in result["error"]
    assert saved[-1]["mailbox_action"] == "move_failed"


def test_wrong_uid_or_uidvalidity_does_not_move_unrelated_message(monkeypatch, stored_email):
    patch_db(monkeypatch, stored_email)
    fake = FakeImap(message_id="<different@example.test>")
    credentials = {"provider": "Gmail", "username": "session@gmail.com", "password": "token", "server": "imap.gmail.com", "port": 993}
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: credentials)
    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: fake)
    monkeypatch.setattr(auto_scan, "close_imap", lambda mail: None)

    result = MailProviderAdapter.move_to_spam("doc-1", "test", "visitor-1")

    assert result["mailbox_moved"] is False
    assert fake.moves == []
    assert "identity" in result["error"]


def test_restore_uses_spam_message_and_session_credentials(monkeypatch, stored_email):
    stored_email = {**stored_email, "mailbox_action": "moved_to_spam", "provider_folder": "[Gmail]/Spam", "provider_uidvalidity": "8"}
    saved = patch_db(monkeypatch, stored_email)
    fake = FakeImap()
    credentials = {"provider": "Gmail", "username": "session@gmail.com", "password": "token", "server": "imap.gmail.com", "port": 993}
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: credentials)
    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: fake)
    monkeypatch.setattr(auto_scan, "close_imap", lambda mail: None)

    result = MailProviderAdapter.restore_from_spam("doc-1", "visitor-1")

    assert result["ok"] is True
    assert result["mailbox_restored"] is True
    assert saved[-1]["mailbox_action"] == "restored"
    assert fake.moves[-1] == ("42", '"INBOX"')


def test_legacy_junk_status_remains_restorable(monkeypatch, stored_email):
    stored_email = {**stored_email, "mailbox_action": "moved_to_junk", "provider_folder": "[Gmail]/Spam", "provider_uidvalidity": "8"}
    patch_db(monkeypatch, stored_email)
    fake = FakeImap()
    credentials = {"provider": "Gmail", "username": "session@gmail.com", "password": "token", "server": "imap.gmail.com", "port": 993}
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: credentials)
    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: fake)
    monkeypatch.setattr(auto_scan, "close_imap", lambda mail: None)

    result = MailProviderAdapter.restore_from_spam("doc-1", "visitor-1")

    assert result["mailbox_restored"] is True


def test_manual_message_is_local_only(monkeypatch):
    manual = {"id": "manual", "message_id": "<manual@example.test>", "folder": "inbox", "mailbox_action": "none"}
    saved = patch_db(monkeypatch, manual)
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: {"username": "session@gmail.com", "password": "token"})

    result = MailProviderAdapter.move_to_spam("manual", "test", "visitor-1")

    assert result["mailbox_moved"] is False
    assert result["local_quarantined"] is True
    assert saved[-1]["mailbox_action"] == "local_only"


def test_repeated_quarantine_does_not_move_again(monkeypatch, stored_email):
    stored = {**stored_email, "folder": "spam", "mailbox_action": "moved_to_spam"}
    patch_db(monkeypatch, stored)
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: None)

    result = MailProviderAdapter.move_to_spam("doc-1", "repeat", "visitor-1")

    assert result["ok"] is True
    assert result["mailbox_moved"] is True


def test_move_refusal_and_auth_failure_are_reported(monkeypatch, stored_email):
    patch_db(monkeypatch, stored_email)
    credentials = {"provider": "Gmail", "username": "session@gmail.com", "password": "token", "server": "imap.gmail.com", "port": 993}
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: credentials)
    fake = FakeImap()
    fake.refuse_move = True
    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: fake)
    monkeypatch.setattr(auto_scan, "close_imap", lambda mail: None)

    result = MailProviderAdapter.move_to_spam("doc-1", "test", "visitor-1")
    assert result["mailbox_moved"] is False
    assert "refused" in result["error"]

    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: (_ for _ in ()).throw(ConnectionError("bad auth")))
    result = MailProviderAdapter.move_to_spam("doc-1", "test", "visitor-1")
    assert result["mailbox_moved"] is False
    assert "connected mailbox" in result["error"]


def test_copy_store_expunge_fallback_checks_operations(monkeypatch, stored_email):
    patch_db(monkeypatch, stored_email)
    fake = FakeImap()
    fake.capabilities = ()
    credentials = {"provider": "Gmail", "username": "session@gmail.com", "password": "token", "server": "imap.gmail.com", "port": 993}
    monkeypatch.setattr(MailProviderAdapter, "get_decrypted_credentials", lambda user_id: credentials)
    monkeypatch.setattr(auto_scan, "open_imap", lambda **kwargs: fake)
    monkeypatch.setattr(auto_scan, "close_imap", lambda mail: None)

    result = MailProviderAdapter.move_to_spam("doc-1", "test", "visitor-1")

    assert result["mailbox_moved"] is True

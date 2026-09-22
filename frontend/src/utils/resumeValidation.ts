const MAX_RESUME_BYTES = 10 * 1024 * 1024;

const RESUME_TYPES = {
  '.pdf': ['application/pdf'],
  '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  '.txt': ['text/plain'],
} as const;

export function validateResumeFile(file: File): string | null {
  const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}` as keyof typeof RESUME_TYPES;
  const allowedTypes = RESUME_TYPES[extension];

  if (!allowedTypes) {
    return 'Please choose a PDF, DOCX, or TXT resume.';
  }

  if (file.size > MAX_RESUME_BYTES) {
    return 'Resume files must be 10MB or smaller.';
  }

  if (file.type && !allowedTypes.includes(file.type as never)) {
    return `The selected ${extension.slice(1).toUpperCase()} file type is not recognized by your browser.`;
  }

  return null;
}

export const RESUME_ACCEPT = '.pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain';
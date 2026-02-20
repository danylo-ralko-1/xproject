import fs from "fs";
import path from "path";

const PROJECTS_DIR = path.resolve(process.cwd(), "../projects");

export interface ChatMessage {
  id: string;
  role: "user" | "system";
  text: string;
  files?: { name: string; savedTo: string }[];
  timestamp: string;
}

function chatLogPath(projectName: string): string {
  return path.join(PROJECTS_DIR, projectName, "output", "chat_log.json");
}

export function getChatLog(projectName: string): ChatMessage[] {
  const p = chatLogPath(projectName);
  if (!fs.existsSync(p)) return [];
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8"));
  } catch {
    return [];
  }
}

export function appendMessage(
  projectName: string,
  message: ChatMessage
): void {
  const messages = getChatLog(projectName);
  messages.push(message);
  const p = chatLogPath(projectName);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(messages, null, 2));
}

/**
 * Categorize a file based on user intent keywords in the message text.
 * Returns the subdirectory within the project where the file should be saved.
 */
export function categorizeFile(
  messageText: string
): "input" | "answers" | "changes" {
  const lower = messageText.toLowerCase();

  const changeKeywords = [
    "change request",
    "change",
    "scope change",
    "cr",
    "update from client",
    "client wants to change",
    "modify",
    "revision",
  ];
  const answerKeywords = [
    "answer",
    "client answer",
    "response",
    "client response",
    "reply",
    "clarification",
    "feedback",
  ];

  for (const kw of changeKeywords) {
    if (lower.includes(kw)) return "changes";
  }
  for (const kw of answerKeywords) {
    if (lower.includes(kw)) return "answers";
  }
  return "input";
}

/**
 * Determine what terminal command to suggest after a file is saved.
 */
export function suggestNextCommand(
  projectName: string,
  category: "input" | "answers" | "changes"
): string {
  switch (category) {
    case "input":
      return `xproject ingest ${projectName}`;
    case "answers":
      return `Say "create breakdown" or "update breakdown" in Claude Code`;
    case "changes":
      return `Say "process change request" in Claude Code`;
  }
}

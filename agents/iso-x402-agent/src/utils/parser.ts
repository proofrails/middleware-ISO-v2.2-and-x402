export interface ParsedCommand {
  action: string;
  args: Record<string, any>;
}

/**
 * Parse command with AI fallback support.
 * 
 * Tries simple parsing first, falls back to AI if enabled.
 */
export async function parseCommandWithAI(
  message: string,
  aiMode: string = 'simple',
  apiUrl?: string,
  systemPrompt?: string
): Promise<ParsedCommand | null> {
  // Always try simple parsing first (fast and free)
  const simpleResult = parseSimpleCommand(message);
  if (simpleResult) {
    return simpleResult;
  }

  // If AI is enabled and simple parsing failed, use AI
  if (aiMode === 'shared' || aiMode === 'custom') {
    try {
      const aiResult = await parseWithAI(message, apiUrl, systemPrompt);
      return aiResult;
    } catch (error) {
      console.error('AI parsing failed:', error);
      return null;
    }
  }

  return null;
}

/**
 * Parse using AI (shared or custom mode)
 */
async function parseWithAI(
  message: string,
  apiUrl?: string,
  systemPrompt?: string
): Promise<ParsedCommand | null> {
  if (!apiUrl) {
    throw new Error('API URL required for AI parsing');
  }

  const response = await fetch(`${apiUrl}/v1/ai/parse-command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      system_prompt: systemPrompt,
    }),
  });

  if (!response.ok) {
    throw new Error('AI parsing request failed');
  }

  const data = await response.json() as any;
  if (data.success && data.parsed_command) {
    return data.parsed_command as ParsedCommand;
  }

  return null;
}

/**
 * Simple command parsing (no AI)
 */
export function parseSimpleCommand(message: string): ParsedCommand | null {
  const trimmed = message.trim().toLowerCase();

  // Help command
  if (trimmed === 'help' || trimmed === '?') {
    return { action: 'help', args: {} };
  }

  // List receipts command
  if (trimmed.startsWith('list')) {
    const parts = trimmed.split(' ');
    return {
      action: 'list',
      args: {
        limit: parts[1] ? parseInt(parts[1]) : 10,
      },
    };
  }

  // Get receipt command
  if (trimmed.startsWith('get ')) {
    const receiptId = trimmed.substring(4).trim();
    return {
      action: 'get',
      args: { receiptId },
    };
  }

  // Verify bundle command
  if (trimmed.startsWith('verify ')) {
    const bundleUrl = trimmed.substring(7).trim();
    return {
      action: 'verify',
      args: { bundleUrl },
    };
  }

  // Generate statement command
  if (trimmed.startsWith('statement ')) {
    const dateStr = trimmed.substring(10).trim();
    return {
      action: 'statement',
      args: { date: dateStr },
    };
  }

  // Refund command
  if (trimmed.startsWith('refund ')) {
    const parts = trimmed.substring(7).trim().split(' ');
    return {
      action: 'refund',
      args: {
        receiptId: parts[0],
        reason: parts.slice(1).join(' ') || 'Customer request',
      },
    };
  }

  // Status command
  if (trimmed.startsWith('status ')) {
    return {
      action: 'status',
      args: { receiptId: trimmed.substring(7).trim() },
    };
  }

  // Anchor command — rest of text is raw JSON to hash
  if (trimmed.startsWith('anchor ')) {
    const raw = message.trim().substring(7).trim(); // preserve original case
    return {
      action: 'anchor',
      args: { data: raw },
    };
  }

  // List anchors command
  if (trimmed === 'list anchors' || trimmed.startsWith('list anchors ')) {
    const days = parseInt(trimmed.split(' ')[2] ?? '7', 10) || 7;
    return { action: 'list-anchors', args: { days } };
  }

  // Verify anchor command
  if (trimmed.startsWith('verify anchor ')) {
    return {
      action: 'verify-anchor',
      args: { hash: trimmed.substring(14).trim() },
    };
  }

  return null;
}

// Export both for backward compatibility
export function parseCommand(message: string): ParsedCommand | null {
  return parseSimpleCommand(message);
}

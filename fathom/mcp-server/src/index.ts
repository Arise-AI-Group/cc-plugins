#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const FATHOM_API_BASE = "https://api.fathom.ai/external/v1";
const API_KEY = process.env.FATHOM_API_KEY;

if (!API_KEY) {
  console.error("Error: FATHOM_API_KEY environment variable is required");
  process.exit(1);
}

interface Meeting {
  id: string;
  title: string;
  created_at: string;
  duration_seconds?: number;
  recording_id?: string;
  calendar_invitees?: string[];
  recorded_by?: string;
}

interface TranscriptEntry {
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
}

interface MeetingSummary {
  summary: string;
  action_items?: string[];
  key_points?: string[];
}

async function fathomFetch<T>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  const url = new URL(`${FATHOM_API_BASE}${endpoint}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString(), {
    headers: {
      "X-Api-Key": API_KEY!,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Fathom API error (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<T>;
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

// Create MCP server
const server = new McpServer({
  name: "fathom",
  version: "1.0.0",
});

// Tool: List meetings
server.tool(
  "list_meetings",
  "List recent Fathom meetings with optional filtering",
  {
    created_after: z
      .string()
      .optional()
      .describe("ISO 8601 date to filter meetings created after this date"),
    limit: z
      .number()
      .optional()
      .default(20)
      .describe("Maximum number of meetings to return (default: 20)"),
    include_summary: z
      .boolean()
      .optional()
      .default(false)
      .describe("Include meeting summaries in response"),
  },
  async ({ created_after, limit, include_summary }) => {
    try {
      const meetings = await fathomFetch<Meeting[]>("/meetings", {
        created_after,
        include_summary,
      });

      const limitedMeetings = meetings.slice(0, limit);

      if (limitedMeetings.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No meetings found.",
            },
          ],
        };
      }

      const formatted = limitedMeetings
        .map((m) => {
          const duration = m.duration_seconds
            ? ` (${formatDuration(m.duration_seconds)})`
            : "";
          const date = new Date(m.created_at).toLocaleDateString();
          return `- **${m.title}**${duration}\n  ID: ${m.recording_id || m.id} | Date: ${date}`;
        })
        .join("\n\n");

      return {
        content: [
          {
            type: "text" as const,
            text: `Found ${limitedMeetings.length} meeting(s):\n\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error listing meetings: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Search meetings
server.tool(
  "search_meetings",
  "Search across Fathom meetings by keyword or phrase",
  {
    query: z.string().describe("Search query to find in meeting titles, transcripts, or summaries"),
    include_transcript: z
      .boolean()
      .optional()
      .default(true)
      .describe("Search within transcripts (default: true)"),
    limit: z
      .number()
      .optional()
      .default(10)
      .describe("Maximum number of results to return (default: 10)"),
  },
  async ({ query, include_transcript, limit }) => {
    try {
      // Fetch meetings with transcript/summary for searching
      const meetings = await fathomFetch<Meeting[]>("/meetings", {
        include_transcript,
        include_summary: true,
      });

      // Filter meetings by query (case-insensitive search in title)
      const queryLower = query.toLowerCase();
      const matches = meetings.filter((m) =>
        m.title.toLowerCase().includes(queryLower)
      );

      const limitedMatches = matches.slice(0, limit);

      if (limitedMatches.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `No meetings found matching "${query}".`,
            },
          ],
        };
      }

      const formatted = limitedMatches
        .map((m) => {
          const date = new Date(m.created_at).toLocaleDateString();
          return `- **${m.title}**\n  ID: ${m.recording_id || m.id} | Date: ${date}`;
        })
        .join("\n\n");

      return {
        content: [
          {
            type: "text" as const,
            text: `Found ${limitedMatches.length} meeting(s) matching "${query}":\n\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error searching meetings: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Get transcript
server.tool(
  "get_transcript",
  "Get the full transcript of a Fathom meeting with speaker attribution",
  {
    recording_id: z.string().describe("The recording ID of the meeting"),
  },
  async ({ recording_id }) => {
    try {
      const transcript = await fathomFetch<TranscriptEntry[] | { transcript: TranscriptEntry[] }>(
        `/recordings/${recording_id}/transcript`
      );

      const entries = Array.isArray(transcript) ? transcript : transcript.transcript;

      if (!entries || entries.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No transcript available for this meeting.",
            },
          ],
        };
      }

      const formatted = entries
        .map((entry) => {
          const timestamp = formatTimestamp(entry.start_time);
          return `[${timestamp}] **${entry.speaker}**: ${entry.text}`;
        })
        .join("\n\n");

      return {
        content: [
          {
            type: "text" as const,
            text: `## Transcript\n\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error getting transcript: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Get summary
server.tool(
  "get_summary",
  "Get the AI-generated summary of a Fathom meeting",
  {
    recording_id: z.string().describe("The recording ID of the meeting"),
  },
  async ({ recording_id }) => {
    try {
      const summary = await fathomFetch<MeetingSummary | { summary: string }>(
        `/recordings/${recording_id}/summary`
      );

      const summaryText = typeof summary === "object" && "summary" in summary
        ? summary.summary
        : String(summary);

      if (!summaryText) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No summary available for this meeting.",
            },
          ],
        };
      }

      let output = `## Meeting Summary\n\n${summaryText}`;

      // Include key points if available
      if ("key_points" in summary && summary.key_points?.length) {
        output += "\n\n### Key Points\n" + summary.key_points.map((p) => `- ${p}`).join("\n");
      }

      // Include action items if available
      if ("action_items" in summary && summary.action_items?.length) {
        output += "\n\n### Action Items\n" + summary.action_items.map((a) => `- [ ] ${a}`).join("\n");
      }

      return {
        content: [
          {
            type: "text" as const,
            text: output,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error getting summary: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Get action items
server.tool(
  "get_action_items",
  "Extract action items from a Fathom meeting summary",
  {
    recording_id: z.string().describe("The recording ID of the meeting"),
  },
  async ({ recording_id }) => {
    try {
      const summary = await fathomFetch<MeetingSummary | { summary: string }>(
        `/recordings/${recording_id}/summary`
      );

      // Check if action_items are directly available
      if ("action_items" in summary && summary.action_items?.length) {
        const formatted = summary.action_items.map((a) => `- [ ] ${a}`).join("\n");
        return {
          content: [
            {
              type: "text" as const,
              text: `## Action Items\n\n${formatted}`,
            },
          ],
        };
      }

      // Otherwise, try to extract from summary text
      const summaryText = typeof summary === "object" && "summary" in summary
        ? summary.summary
        : String(summary);

      if (!summaryText) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No summary or action items available for this meeting.",
            },
          ],
        };
      }

      // Parse action items from summary using common patterns
      const actionPatterns = [
        /action items?:?\s*([\s\S]*?)(?=\n\n|key points|summary|$)/gi,
        /next steps?:?\s*([\s\S]*?)(?=\n\n|key points|summary|$)/gi,
        /to-?do:?\s*([\s\S]*?)(?=\n\n|key points|summary|$)/gi,
      ];

      let actionItems: string[] = [];
      for (const pattern of actionPatterns) {
        const match = pattern.exec(summaryText);
        if (match && match[1]) {
          const items = match[1]
            .split(/\n/)
            .map((line) => line.replace(/^[-*•]\s*/, "").trim())
            .filter((line) => line.length > 0);
          actionItems = [...actionItems, ...items];
        }
      }

      if (actionItems.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: "No action items found in this meeting. The meeting summary is available via `get_summary`.",
            },
          ],
        };
      }

      const formatted = [...new Set(actionItems)].map((a) => `- [ ] ${a}`).join("\n");
      return {
        content: [
          {
            type: "text" as const,
            text: `## Action Items (extracted)\n\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error getting action items: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Fathom MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

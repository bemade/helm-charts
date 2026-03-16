/**
 * OpenClaw Channel Plugin for Odoo Discuss
 * 
 * Enables Majordomo to receive and respond to messages from Odoo Discuss.
 */

import type { ChannelPlugin, ChannelPluginContext } from "openclaw/plugin-sdk/core";

const PLUGIN_ID = "odoo-discuss";

interface OdooDiscussConfig {
  enabled: boolean;
  token: string;
  odooUrl: string;
  odooDatabase?: string;
  odooUser?: string;
  odooApiKey?: string;
  webhookPath: string;
  allowedUserIds?: number[];
  dmPolicy: "allowlist" | "open" | "disabled";
  rateLimitPerMinute?: number;
}

interface OdooWebhookPayload {
  message_id: number;
  channel_id: number;
  author_id: number;
  author_name: string;
  body: string;
  timestamp: string;
  token: string;
}

/**
 * Send a message to Odoo via JSON-RPC
 */
async function sendToOdoo(
  odooUrl: string,
  database: string,
  userId: number,
  apiKey: string,
  channelId: number,
  body: string
): Promise<{ ok: boolean; error?: string }> {
  const endpoint = `${odooUrl}/jsonrpc`;
  
  const payload = {
    jsonrpc: "2.0",
    method: "call",
    id: Date.now(),
    params: {
      service: "object",
      method: "execute",
      args: [
        database,
        userId,
        apiKey,
        "mail.message",
        "create",
        {
          model: "discuss.channel",
          res_id: channelId,
          body: body,
          message_type: "comment",
          subtype_id: 1, // "Discussions"
        },
      ],
    },
  };

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    
    if (result.error) {
      return { ok: false, error: result.error.message || "Odoo RPC error" };
    }
    
    return { ok: true };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/**
 * The channel plugin definition
 */
const plugin: ChannelPlugin = {
  id: PLUGIN_ID,
  meta: {
    id: PLUGIN_ID,
    label: "Odoo Discuss",
    selectionLabel: "Odoo Discuss (Bemade)",
    docsPath: "/channels/odoo-discuss",
    blurb: "Chat with Majordomo from Odoo Discuss",
    aliases: ["odoo", "discuss"],
  },

  capabilities: {
    chatTypes: ["direct", "channel"],
    supportsReactions: false,
    supportsEdits: false,
    supportsThreads: false,
    supportsMedia: false,
  },

  config: {
    listAccountIds: (cfg) => {
      const channelCfg = cfg.channels?.[PLUGIN_ID];
      if (!channelCfg) return [];
      if (channelCfg.accounts) {
        return Object.keys(channelCfg.accounts);
      }
      return ["default"];
    },

    resolveAccount: (cfg, accountId) => {
      const channelCfg = cfg.channels?.[PLUGIN_ID];
      if (!channelCfg) return { accountId: accountId || "default" };

      if (channelCfg.accounts && accountId) {
        return {
          accountId,
          ...channelCfg.accounts[accountId],
        };
      }

      if (channelCfg.accounts?.default) {
        return { accountId: "default", ...channelCfg.accounts.default };
      }

      // Single-account config
      return {
        accountId: accountId || "default",
        ...channelCfg,
      };
    },
  },

  outbound: {
    deliveryMode: "direct",

    sendText: async ({ text, target, config }) => {
      const cfg = config as unknown as OdooDiscussConfig;
      const accountCfg = cfg.accounts?.[target.accountId || "default"] || cfg;
      
      const result = await sendToOdoo(
        accountCfg.odooUrl,
        accountCfg.odooDatabase || "odoo",
        parseInt(accountCfg.odooUser || "2"),
        accountCfg.odooApiKey || "",
        parseInt(target.chatId),
        text
      );

      if (!result.ok) {
        throw new Error(`Failed to send to Odoo: ${result.error}`);
      }

      return { ok: true };
    },
  },
};

/**
 * Plugin entry point - registers the channel and webhook route
 */
export default function register(api: ChannelPluginContext) {
  // Register the channel
  api.registerChannel({ plugin });

  // Register the webhook HTTP route
  api.registerHttpRoute({
    path: "/webhook/odoo-discuss",
    auth: "plugin",
    match: "exact",
    handler: async (req, res) => {
      if (req.method !== "POST") {
        res.statusCode = 405;
        res.end(JSON.stringify({ error: "Method not allowed" }));
        return true;
      }

      let body = "";
      req.on("data", (chunk) => (body += chunk));
      req.on("end", async () => {
        try {
          const payload: OdooWebhookPayload = JSON.parse(body);
          const cfg = api.config.channels?.[PLUGIN_ID] as OdooDiscussConfig;

          // Validate token
          if (!cfg || payload.token !== cfg.token) {
            res.statusCode = 401;
            res.end(JSON.stringify({ error: "Invalid token" }));
            return;
          }

          // Check allowlist if configured
          if (cfg.dmPolicy === "allowlist" && cfg.allowedUserIds?.length) {
            if (!cfg.allowedUserIds.includes(payload.author_id)) {
              res.statusCode = 403;
              res.end(JSON.stringify({ error: "User not authorized" }));
              return;
            }
          }

          // Respond OK to Odoo immediately
          res.statusCode = 200;
          res.end(JSON.stringify({ ok: true }));

          // Inject message into OpenClaw for processing
          // This triggers the agent to process and respond
          api.injectMessage?.({
            channel: PLUGIN_ID,
            chatId: String(payload.channel_id),
            senderId: String(payload.author_id),
            senderName: payload.author_name,
            text: payload.body,
            messageId: String(payload.message_id),
          });
        } catch (err) {
          api.logger.error("Odoo webhook error:", err);
          res.statusCode = 400;
          res.end(JSON.stringify({ error: "Invalid payload" }));
        }
      });

      return true;
    },
  });

  api.logger.info("Odoo Discuss plugin loaded");
}
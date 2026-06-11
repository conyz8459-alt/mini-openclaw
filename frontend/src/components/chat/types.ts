// 前端对话消息模型

export interface ToolStep {
  name: string;
  input: Record<string, unknown>;
  output?: string;
}

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  // 助手消息在生成过程中产生的工具调用（思考链）
  toolSteps?: ToolStep[];
  // 是否正在流式生成
  streaming?: boolean;
  // 本轮 token 用量（仅助手消息，流式结束后填充）
  usage?: TokenUsage;
}

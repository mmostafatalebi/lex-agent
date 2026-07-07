import type {
  AnalysisStatusResponse,
  HumanDecision,
  ResultsResponse,
  UploadContractResponse,
} from "./api-types";
import { mockBackend } from "./mock-server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

const API_KEY_STORAGE = "apiKey";
const REQUIRE_KEY_OVERRIDE = "lexagent.requireApiKey";

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function requireApiKey(): boolean {
  if (typeof window !== "undefined") {
    // Test seam: exercise the gated flow without a separate build.
    if (window.localStorage.getItem(REQUIRE_KEY_OVERRIDE) === "true") return true;
  }
  return process.env.NEXT_PUBLIC_REQUIRE_API_KEY === "true";
}

export function getStoredApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(API_KEY_STORAGE);
}

export function setStoredApiKey(key: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(API_KEY_STORAGE, key.trim());
}

async function fileToBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export class ApiClient {
  constructor(
    private baseUrl: string,
    private apiKey: string | null
  ) {}

  private headers(): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (requireApiKey() && this.apiKey) {
      headers["x-api-key"] = this.apiKey;
    }
    return headers;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, { ...init, headers: this.headers() });
    } catch {
      throw new ApiError(0, "Could not reach the API. Check the API URL and your connection.");
    }
    if (!response.ok) {
      const message = await this.readError(response);
      throw new ApiError(response.status, message);
    }
    return (await response.json()) as T;
  }

  private async readError(response: Response): Promise<string> {
    try {
      const body = (await response.json()) as { message?: string };
      if (body.message) return body.message;
    } catch {
      // fall through to a generic message
    }
    return `Request failed with status ${response.status}`;
  }

  async uploadContract(file: File): Promise<UploadContractResponse> {
    if (USE_MOCK) return mockBackend.uploadContract(file);
    const content_base64 = await fileToBase64(file);
    return this.request<UploadContractResponse>("/contracts", {
      method: "POST",
      body: JSON.stringify({ filename: file.name, content_base64 }),
    });
  }

  async startAnalysis(contractId: string): Promise<AnalysisStatusResponse> {
    if (USE_MOCK) return mockBackend.startAnalysis(contractId);
    return this.request<AnalysisStatusResponse>("/analyses", {
      method: "POST",
      body: JSON.stringify({ contract_id: contractId }),
    });
  }

  async getAnalysis(threadId: string): Promise<AnalysisStatusResponse> {
    if (USE_MOCK) return mockBackend.getAnalysis(threadId);
    return this.request<AnalysisStatusResponse>(`/analyses/${threadId}`, { method: "GET" });
  }

  async submitDecisions(
    threadId: string,
    decisions: HumanDecision[]
  ): Promise<AnalysisStatusResponse> {
    if (USE_MOCK) return mockBackend.submitDecisions(threadId, decisions);
    return this.request<AnalysisStatusResponse>(`/analyses/${threadId}/decisions`, {
      method: "POST",
      body: JSON.stringify({ decisions }),
    });
  }

  async getResults(threadId: string): Promise<ResultsResponse> {
    if (USE_MOCK) return mockBackend.getResults(threadId);
    return this.request<ResultsResponse>(`/analyses/${threadId}/results`, { method: "GET" });
  }
}

export function getClient(): ApiClient {
  return new ApiClient(API_URL, getStoredApiKey());
}

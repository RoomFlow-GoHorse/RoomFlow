interface ApiEnvelope<T> {
  data: T
}

interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    details?: unknown
  }
  detail?: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    public readonly details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface IHttpClient {
  request<T>(path: string, init?: RequestInit, authenticated?: boolean): Promise<T>
}

// centralização
export class HttpClient implements IHttpClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getToken: () => string | null,
  ) {}

  async request<T>(
    path: string,
    init: RequestInit = {},
    authenticated = true,
  ): Promise<T> {
    // organiza cabeçalhos e adiciona tokens
    const token = authenticated ? this.getToken() : null
    const headers = new Headers(init.headers)
    headers.set('Accept', 'application/json')

    if (init.body) {
      headers.set('Content-Type', 'application/json')
    }
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    // converte falhas
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${path}`, { ...init, headers })
    } catch {
      throw new ApiError(
        'Não foi possível conectar à API do RoomFlow. Verifique se o backend está em execução.',
        0,
      )
    }

    const body = (await response.json().catch(() => null)) as
      | ApiEnvelope<T>
      | ApiErrorBody
      | null

    if (!response.ok) {
      const error = body && 'error' in body ? body.error : undefined
      const detail = body && 'detail' in body ? body.detail : undefined
      throw new ApiError(
        error?.message ?? detail ?? `A API retornou o status HTTP ${response.status}.`,
        response.status,
        error?.code,
        error?.details,
      )
    }

    if (!body || !('data' in body)) {
      throw new ApiError('A API retornou uma resposta em formato inesperado.', response.status)
    }

    return body.data
  }
}

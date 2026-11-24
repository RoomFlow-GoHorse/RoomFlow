import type {
  AuthenticatedUser,
  InstitutionOption,
  Session,
} from '@/models/roomflow'
import { ApiError, type IHttpClient } from './HttpClient'

interface LoginResponse {
  access_token: string
  expires_at: string
  user: AuthenticatedUser
}

// usuario precisa escolher uma instituição
export class InstitutionSelectionError extends Error {
  constructor(public readonly institutions: InstitutionOption[]) {
    super('Selecione a instituição para acessar.')
    this.name = 'InstitutionSelectionError'
  }
}

export interface IAuthService {
  login(email: string, password: string, institutionId?: string): Promise<Session>
  identify(): Promise<AuthenticatedUser>
  logout(): Promise<void>
}

//adiciona login, identificação e logout
export class AuthService implements IAuthService {
  constructor(private readonly client: IHttpClient) {}

  async login(
    email: string,
    password: string,
    institutionId?: string,
  ): Promise<Session> {
    // tradução para o modelo do frontend
    try {
      const result = await this.client.request<LoginResponse>(
        '/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({
            email,
            password,
            institution_id: institutionId || null,
          }),
        },
        false,
      )

      return {
        accessToken: result.access_token,
        expiresAt: result.expires_at,
        user: result.user,
      }
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.code === 'institution_selection_required' &&
        Array.isArray(error.details)
      ) {
        throw new InstitutionSelectionError(
          error.details.filter(
            (item): item is InstitutionOption =>
              typeof item === 'object' &&
              item !== null &&
              'institution_id' in item &&
              typeof item.institution_id === 'string',
          ),
        )
      }
      throw error
    }
  }

  identify(): Promise<AuthenticatedUser> {
    // Confirma o token atual
    return this.client.request('/auth/me')
  }

  async logout(): Promise<void> {
    await this.client.request('/auth/logout', { method: 'POST' })
  }
}

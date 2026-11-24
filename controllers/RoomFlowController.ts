import type {
  Reservation,
  ReservationInput,
  Session,
  SpaceCatalog,
} from '@/models/roomflow'
import type { IAuthService } from '@/services/AuthService'
import type { IReservationService } from '@/services/ReservationService'

const SESSION_KEY = 'roomflow.session'

export interface DashboardData {
  reservations: Reservation[]
  catalog: SpaceCatalog
}

//autenticação, sessão e reservas entre as views e serviços
export class RoomFlowController {
  constructor(
    private readonly authService: IAuthService,
    private readonly reservationService: IReservationService,
  ) {}

  getStoredSession(): Session | null {
    const stored = sessionStorage.getItem(SESSION_KEY)
    if (!stored) return null

    try {
      const session = JSON.parse(stored) as Session
      if (new Date(session.expiresAt).getTime() <= Date.now()) {
        this.clearSession()
        return null
      }
      return session
    } catch {
      this.clearSession()
      return null
    }
  }

  async login(
    email: string,
    password: string,
    institutionId?: string,
  ): Promise<Session> {
    // armazena a sessão
    const session = await this.authService.login(email, password, institutionId)
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    return session
  }

  async restoreSession(): Promise<Session | null> {
    // reutiliza uma sessão anteriormente armazenada no backend
    const session = this.getStoredSession()
    if (!session) return null

    try {
      const user = await this.authService.identify()
      const restored = { ...session, user }
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(restored))
      return restored
    } catch {
      this.clearSession()
      return null
    }
  }

  async loadDashboard(): Promise<DashboardData> {
    // carrega reservas em menos tempo
    const [reservations, catalog] = await Promise.all([
      this.reservationService.listOwn(),
      this.reservationService.getCatalog(),
    ])
    return { reservations, catalog }
  }

  async createReservation(input: ReservationInput): Promise<DashboardData> {
    // cria reserva
    await this.reservationService.create(input)
    return this.loadDashboard()
  }

  async cancelReservation(id: string, reason?: string): Promise<DashboardData> {
    // cancela reserva
    await this.reservationService.cancel(id, reason)
    return this.loadDashboard()
  }

  async logout(): Promise<void> {
    // encerra a sessão e limpa a sessão local
    try {
      await this.authService.logout()
    } finally {
      this.clearSession()
    }
  }

  private clearSession(): void {
    sessionStorage.removeItem(SESSION_KEY)
  }
}

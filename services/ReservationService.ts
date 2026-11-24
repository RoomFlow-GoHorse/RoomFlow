import type {
  Reservation,
  ReservationInput,
  SpaceCatalog,
} from '@/models/roomflow'
import type { IHttpClient } from './HttpClient'

export interface IReservationService {
  listOwn(): Promise<Reservation[]>
  getCatalog(start?: string, end?: string): Promise<SpaceCatalog>
  create(input: ReservationInput): Promise<Reservation>
  cancel(id: string, reason?: string): Promise<Reservation>
}

// conexão de reservas
export class ReservationService implements IReservationService {
  constructor(private readonly client: IHttpClient) {}

  listOwn(): Promise<Reservation[]> {
    return this.client.request('/reservations/mine')
  }

  getCatalog(start?: string, end?: string): Promise<SpaceCatalog> {
    // filtragem no catálogo
    const query =
      start && end
        ? `?${new URLSearchParams({ start, end }).toString()}`
        : ''
    return this.client.request(`/reservations/spaces${query}`)
  }

  create(input: ReservationInput): Promise<Reservation> {
    // cria uma solicitação de reserva
    return this.client.request('/reservations', {
      method: 'POST',
      body: JSON.stringify(input),
    })
  }

  cancel(id: string, reason?: string): Promise<Reservation> {
    // cancela uma reserva
    return this.client.request(`/reservations/${encodeURIComponent(id)}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || null }),
    })
  }
}

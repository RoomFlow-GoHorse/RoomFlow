//perfis que podem ser autenticados
export type UserProfile = 'admin' | 'gerente' | 'solicitante' | 'participante'

export interface AuthenticatedUser {
  id: string
  name: string
  email: string
  profile: UserProfile
  institution_id: string | null
  phone: string | null
}

export interface Session {
  accessToken: string
  expiresAt: string
  user: AuthenticatedUser
}

export interface InstitutionOption {
  institution_id: string
}

//catálogo de salas e espaços
export interface Space {
  id: string
  name: string
  type: string
  building: string
  building_id: string
  location: string
  capacity: number
  resources: string[]
}

export interface SpaceCatalog {
  timezone: string
  justification_required: boolean
  spaces: Space[]
}

//ler e criar reservas
export type ReservationStatus =
  | 'pendente'
  | 'em_analise'
  | 'aprovada'
  | 'rejeitada'
  | 'cancelada'

export interface Reservation {
  id: string
  space_id: string
  space_name: string
  requester_name: string
  title: string
  activity_type: string
  start: string
  end: string
  participants: number
  justification: string | null
  status: ReservationStatus
  has_overlap: boolean
  created_at: string
  reviewed_at: string | null
  decision_reason: string | null
}

export interface ReservationInput {
  space_id: string
  title: string
  activity_type: string
  start: string
  end: string
  participants: number
  justification: string | null
}

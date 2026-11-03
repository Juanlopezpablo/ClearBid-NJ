import { apiClient } from '@/services/api'

export interface SprintPlan { name: string; goal: string; start_date: string; end_date: string }
export interface Sprint extends SprintPlan {
  id: string; application_id: string; status: 'PLANNED' | 'ACTIVE' | 'FINISHED';
  total_tickets: number; completed_tickets: number; progress: number; released_tickets: number
}
export interface SprintTicket {
  id: string; title: string; epic_title: string | null; status: string;
  assignee_id: string | null; assignee: { full_name: string } | null
}
export interface Page<T> { items: T[]; total: number; skip: number; limit: number }

export const sprintApi = {
  list: async (application_id: string, skip = 0) => (await apiClient.get<Page<Sprint>>('/sprints', { params: { application_id, skip, limit: 25 } })).data,
  get: async (id: string) => (await apiClient.get<Sprint>(`/sprints/${id}`)).data,
  create: async (application_id: string, plan: SprintPlan) => (await apiClient.post<Sprint>('/sprints', { ...plan, application_id })).data,
  edit: async (id: string, plan: SprintPlan) => (await apiClient.put<Sprint>(`/sprints/${id}`, plan)).data,
  start: async (id: string) => (await apiClient.post<Sprint>(`/sprints/${id}/start`)).data,
  finish: async (id: string) => (await apiClient.post<Sprint>(`/sprints/${id}/finish`)).data,
  tickets: async (id: string, available: boolean, skip = 0, q = '') => (await apiClient.get<Page<SprintTicket>>(`/sprints/${id}/tickets`, { params: { available, skip, limit: 25, q } })).data,
  add: async (id: string, ticket: string) => { await apiClient.put(`/sprints/${id}/tickets/${ticket}`) },
  remove: async (id: string, ticket: string) => { await apiClient.delete(`/sprints/${id}/tickets/${ticket}`) },
}

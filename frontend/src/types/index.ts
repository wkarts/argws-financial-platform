export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface AuthUser {
  id: string
  name: string
  email: string
  role: string
  permissions: string[]
  companies: string[]
}

export interface AuthSession {
  tokens: TokenPair
  user: AuthUser
  tenant?: { id: string; slug: string; hostname: string; timezone: string }
}

export interface ApiResponse<T> {
  success: boolean
  data: T
}

export interface Paginated<T> {
  success: boolean
  data: T[]
  meta: { page: number; per_page: number; total: number; pages: number }
}

export interface TenantDomain {
  id: string
  hostname: string
  domain_type: string
  status: string
  is_primary: boolean
  is_temporary: boolean
  dns_verified_at?: string
  ssl_status: string
  last_error?: string
}

export interface Tenant {
  id: string
  name: string
  slug: string
  legal_document?: string
  status: string
  plan_code: string
  timezone: string
  features: Record<string, unknown>
  limits: Record<string, unknown>
  created_at: string
  domains: TenantDomain[]
}

export interface Company {
  id: string
  legal_name: string
  trade_name?: string
  tax_id: string
  email?: string
  phone?: string
  address: Record<string, unknown>
  branding: Record<string, unknown>
  is_active: boolean
  created_at: string
}

export interface Customer {
  id: string
  person_type: string
  name: string
  trade_name?: string
  tax_id?: string
  email?: string
  phone?: string
  whatsapp?: string
  address: Record<string, unknown>
  tags: string[]
  is_active: boolean
  created_at: string
}

export interface ServiceItem {
  id: string
  code: string
  name: string
  description?: string
  default_amount: string
  default_frequency: string
  is_active: boolean
}

export interface Contract {
  id: string
  company_id: string
  customer_id: string
  service_id: string
  code: string
  amount: string
  frequency: string
  billing_method: string
  due_day: number
  start_date: string
  end_date?: string
  next_generation_date: string
  status: string
  created_at: string
}

export interface Receivable {
  id: string
  company_id: string
  customer_id: string
  contract_id?: string
  document_number: string
  competence: string
  description: string
  issue_date: string
  due_date: string
  original_amount: string
  discount_amount: string
  interest_amount: string
  fine_amount: string
  paid_amount: string
  balance: string
  status: string
  source: string
  created_at: string
}

export interface Charge {
  id: string
  receivable_id: string
  charge_type: string
  provider: string
  external_id: string
  our_number?: string
  txid?: string
  digitable_line?: string
  barcode?: string
  pix_copy_paste?: string
  document_url?: string
  status: string
  registered_at?: string
}

export interface Payment {
  id: string
  receivable_id: string
  charge_id?: string
  provider: string
  external_id: string
  end_to_end_id?: string
  amount: string
  paid_at: string
  payment_method: string
  status: string
}

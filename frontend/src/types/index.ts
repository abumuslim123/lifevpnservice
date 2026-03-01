export type UserRole = 'admin' | 'manager' | 'viewer'

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ServerStatus = 'online' | 'offline' | 'unknown' | 'connecting'
export type ServerOS = 'ubuntu' | 'debian' | 'centos' | 'fedora' | 'almalinux' | 'other'

export interface Server {
  id: number
  name: string
  ip_address: string
  ssh_port: number
  ssh_user: string
  location?: string
  country_code?: string
  os_type: ServerOS
  status: ServerStatus
  last_check_at?: string
  installed_protocols?: Record<string, boolean>
  notes?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ProtocolType =
  | 'wireguard'
  | 'amnezia_wg'
  | 'openvpn'
  | 'ikev2'
  | 'l2tp'
  | 'pptp'
  | 'xray_vless'
  | 'xray_vmess'
  | 'xray_trojan'
  | 'xray_shadowsocks'

export type ProxyType = 'http' | 'https' | 'socks5' | 'shadowsocks' | 'trojan' | 'vmess' | 'vless'

export interface VpnProfile {
  id: number
  name: string
  server_id: number
  active_protocol: ProtocolType
  enabled_protocols: ProtocolType[]
  client_id?: number
  user_id?: number
  is_active: boolean
  credentials?: Record<string, string>
  notes?: string
  created_at: string
  updated_at: string
}

export interface Client {
  id: number
  name: string
  email?: string
  phone?: string
  telegram?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface ProxyConfig {
  id: number
  name: string
  proxy_type: ProxyType
  server_id: number
  client_id?: number
  user_id?: number
  port: number
  username?: string
  config_data?: Record<string, string>
  is_active: boolean
  notes?: string
  created_at: string
  updated_at: string
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface DashboardStats {
  servers: { total: number; online: number }
  clients: { total: number }
  vpn_profiles: { total: number; active: number }
  proxies: { total: number; active: number }
  users: { total: number }
  servers_list: Array<{
    id: number
    name: string
    ip_address: string
    status: ServerStatus
    location?: string
    last_check_at?: string
  }>
  protocols_distribution: Array<{ protocol: ProtocolType; count: number }>
}

export const PROTOCOL_LABELS: Record<ProtocolType, string> = {
  wireguard: 'WireGuard',
  amnezia_wg: 'AmneziaWG',
  openvpn: 'OpenVPN',
  ikev2: 'IKEv2/IPSec',
  l2tp: 'L2TP/IPSec',
  pptp: 'PPTP',
  xray_vless: 'VLESS (Xray)',
  xray_vmess: 'VMess (Xray)',
  xray_trojan: 'Trojan (Xray)',
  xray_shadowsocks: 'Shadowsocks (Xray)',
}

export const PROXY_LABELS: Record<ProxyType, string> = {
  http: 'HTTP',
  https: 'HTTPS',
  socks5: 'SOCKS5',
  shadowsocks: 'Shadowsocks',
  trojan: 'Trojan',
  vmess: 'VMess',
  vless: 'VLESS',
}

export const CLIENT_APP_OPTIONS = [
  { value: 'wireguard', label: 'WireGuard App (.conf)' },
  { value: 'amnezia', label: 'Amnezia VPN (.vpn)' },
  { value: 'openvpn', label: 'OpenVPN Connect (.ovpn)' },
  { value: 'v2raytun', label: 'v2rayTUN / v2rayNG (.json)' },
  { value: 'clashyaml', label: 'Clash / Clash Meta (.yaml)' },
  { value: 'singbox', label: 'Sing-box (.json)' },
  { value: 'shadowrocket', label: 'Shadowrocket (URI)' },
]

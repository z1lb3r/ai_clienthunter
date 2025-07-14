// frontend/src/services/clientHunterApi.ts
import { 
  ProductTemplate, 
  ProductTemplateCreate, 
  ProductTemplateUpdate,
  MonitoringSettings,
  MonitoringSettingsUpdate,
  PotentialClient,
  ClientStatusUpdate,
  ApiResponse,
  DashboardStats
} from '../types/api';

const API_BASE = 'http://localhost:8000/api/v1/client-monitoring';

class ClientHunterApi {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API request failed');
    }

    return response.json();
  }

  // ==================== PRODUCT TEMPLATES ====================
  
  async getProductTemplates(): Promise<ApiResponse<ProductTemplate[]>> {
    return this.request<ApiResponse<ProductTemplate[]>>('/product-templates');
  }

  async createProductTemplate(template: ProductTemplateCreate): Promise<ApiResponse<ProductTemplate>> {
    return this.request<ApiResponse<ProductTemplate>>('/product-templates', {
      method: 'POST',
      body: JSON.stringify(template),
    });
  }

  async updateProductTemplate(id: number, template: ProductTemplateUpdate): Promise<ApiResponse<ProductTemplate>> {
    return this.request<ApiResponse<ProductTemplate>>(`/product-templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(template),
    });
  }

  async deleteProductTemplate(id: number): Promise<ApiResponse<void>> {
    return this.request<ApiResponse<void>>(`/product-templates/${id}`, {
      method: 'DELETE',
    });
  }

  // ==================== MONITORING SETTINGS ====================
  
  async getMonitoringSettings(): Promise<ApiResponse<MonitoringSettings>> {
    return this.request<ApiResponse<MonitoringSettings>>('/monitoring/settings');
  }

  async updateMonitoringSettings(settings: MonitoringSettingsUpdate): Promise<ApiResponse<MonitoringSettings>> {
    return this.request<ApiResponse<MonitoringSettings>>('/monitoring/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  async startMonitoring(): Promise<ApiResponse<void>> {
    return this.request<ApiResponse<void>>('/monitoring/start', {
      method: 'POST',
    });
  }

  async stopMonitoring(): Promise<ApiResponse<void>> {
    return this.request<ApiResponse<void>>('/monitoring/stop', {
      method: 'POST',
    });
  }

  // ==================== POTENTIAL CLIENTS ====================
  
  async getPotentialClients(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<PotentialClient[]>> {
    const queryParams = new URLSearchParams();
    
    if (params?.status) queryParams.append('status', params.status);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());

    const endpoint = `/potential-clients${queryParams.toString() ? `?${queryParams}` : ''}`;
    return this.request<ApiResponse<PotentialClient[]>>(endpoint);
  }

  async updateClientStatus(clientId: number, statusUpdate: ClientStatusUpdate): Promise<ApiResponse<PotentialClient>> {
    return this.request<ApiResponse<PotentialClient>>(`/potential-clients/${clientId}/status`, {
      method: 'PUT',
      body: JSON.stringify(statusUpdate),
    });
  }

  // ==================== DASHBOARD STATS ====================
  
  async getDashboardStats(): Promise<DashboardStats> {
    // Получаем клиентов и шаблоны
    const [clientsResponse, templatesResponse] = await Promise.all([
      this.getPotentialClients({ limit: 1000 }),
      this.getProductTemplates()
    ]);
    
    const clients = clientsResponse.data || [];
    const templates = templatesResponse.data || [];

    // Подсчитываем уникальные чаты из активных шаблонов
    const uniqueChats = new Set<string>();
    templates
      .filter(template => template.is_active)
      .forEach(template => {
        if (template.chat_ids && Array.isArray(template.chat_ids)) {
          template.chat_ids.forEach(chatId => uniqueChats.add(chatId));
        }
      });

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const clientsToday = clients.filter(client => 
      new Date(client.created_at) >= today
    ).length;

    const clientsWeek = clients.filter(client => 
      new Date(client.created_at) >= weekAgo
    ).length;

    const convertedClients = clients.filter(client => 
      client.client_status === 'converted'
    ).length;

    const conversionRate = clients.length > 0 
      ? Math.round((convertedClients / clients.length) * 100 * 10) / 10 
      : 0;
    
    return {
      clientsToday,
      clientsWeek,
      totalClients: clients.length,
      totalChats: uniqueChats.size, // ✅ Исправлено!
      conversionRate
    };
  }
}

export const clientHunterApi = new ClientHunterApi();
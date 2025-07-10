// frontend/src/hooks/useClientHunterApi.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clientHunterApi } from '../services/clientHunterApi';
import { ProductTemplateCreate, ProductTemplateUpdate, MonitoringSettingsUpdate, ClientStatusUpdate } from '../types/api';

// ==================== QUERY KEYS ====================
export const queryKeys = {
  productTemplates: ['productTemplates'] as const,
  monitoringSettings: ['monitoringSettings'] as const,
  potentialClients: (params?: any) => ['potentialClients', params] as const,
  dashboardStats: ['dashboardStats'] as const,
};

// ==================== PRODUCT TEMPLATES ====================
export const useProductTemplates = () => {
  return useQuery({
    queryKey: queryKeys.productTemplates,
    queryFn: () => clientHunterApi.getProductTemplates(),
  });
};

export const useCreateProductTemplate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (template: ProductTemplateCreate) => 
      clientHunterApi.createProductTemplate(template),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.productTemplates });
    },
  });
};

export const useUpdateProductTemplate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, template }: { id: number; template: ProductTemplateUpdate }) =>
      clientHunterApi.updateProductTemplate(id, template),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.productTemplates });
    },
  });
};

export const useDeleteProductTemplate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: number) => clientHunterApi.deleteProductTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.productTemplates });
    },
  });
};

// ==================== MONITORING SETTINGS ====================
export const useMonitoringSettings = () => {
  return useQuery({
    queryKey: queryKeys.monitoringSettings,
    queryFn: () => clientHunterApi.getMonitoringSettings(),
  });
};

export const useUpdateMonitoringSettings = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (settings: MonitoringSettingsUpdate) =>
      clientHunterApi.updateMonitoringSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.monitoringSettings });
    },
  });
};

export const useStartMonitoring = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => clientHunterApi.startMonitoring(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.monitoringSettings });
    },
  });
};

export const useStopMonitoring = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => clientHunterApi.stopMonitoring(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.monitoringSettings });
    },
  });
};

// ==================== POTENTIAL CLIENTS ====================
export const usePotentialClients = (params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) => {
  return useQuery({
    queryKey: queryKeys.potentialClients(params),
    queryFn: () => clientHunterApi.getPotentialClients(params),
  });
};

export const useUpdateClientStatus = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ clientId, statusUpdate }: { clientId: number; statusUpdate: ClientStatusUpdate }) =>
      clientHunterApi.updateClientStatus(clientId, statusUpdate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['potentialClients'] });
    },
  });
};

// ==================== DASHBOARD STATS ====================
export const useDashboardStats = () => {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: () => clientHunterApi.getDashboardStats(),
  });
};

// ==================== MONITORING CONTROL ====================
export const useStartMonitoring = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => clientHunterApi.startMonitoring(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.monitoringSettings });
    },
  });
};

export const useStopMonitoring = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => clientHunterApi.stopMonitoring(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.monitoringSettings });
    },
  });
};
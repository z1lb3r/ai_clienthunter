// frontend/src/services/telegramService.ts - ОЧИЩЕННАЯ ВЕРСИЯ

import { api } from './api';
import { TelegramGroup, ModeratorMetrics, AnalysisReport } from '../types/telegram';

export const telegramService = {
  // ===== ГРУППЫ =====
  
  async getGroups(): Promise<TelegramGroup[]> {
    const response = await api.get('/telegram/groups');
    return response.data;
  },

  async getGroupDetails(groupId: string): Promise<TelegramGroup> {
    const response = await api.get(`/telegram/groups/${groupId}`);
    return response.data;
  },

  async getGroupMessages(groupId: string): Promise<any[]> {
    const response = await api.get(`/telegram/groups/${groupId}/messages`);
    return response.data;
  },

  async getGroupModerators(groupId: string): Promise<any[]> {
    const response = await api.get(`/telegram/groups/${groupId}/moderators`);
    return response.data;
  },

  // ===== АНАЛИЗ МОДЕРАТОРОВ =====
  
  async analyzeGroup(groupId: string): Promise<AnalysisReport> {
    const response = await api.post(`/telegram/groups/${groupId}/analyze`);
    return response.data;
  },

  // ===== МОДЕРАТОРЫ =====
  
  async getModeratorMetrics(moderatorId: string, groupId: string): Promise<ModeratorMetrics[]> {
    const response = await api.get(`/telegram/moderators/${moderatorId}/metrics`, {
      params: { group_id: groupId }
    });
    return response.data;
  },

  // ===== АНАЛИТИКА =====
  
  async getGroupAnalytics(groupId: string): Promise<any> {
    const response = await api.get(`/telegram/groups/${groupId}/analytics`);
    return response.data;
  }
};
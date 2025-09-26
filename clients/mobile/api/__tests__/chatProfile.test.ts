// clients/mobile/api/__tests__/chatProfile.test.ts
import { getProfile, putProfile, type Profile } from '../chatProfile';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

describe('chatProfile API', () => {
  const apiBase = 'https://test.api.com';
  const token = 'test-token';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getProfile', () => {
    it('should fetch profile successfully', async () => {
      const mockProfile: Profile = {
        consent_personalization: true,
        memory_paused: false,
        allergies: ['peanuts', 'milk'],
        pregnancy_trimester: 2,
        pregnancy_due_date: '2025-06-15',
        child_birthdate: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProfile,
      } as Response);

      const result = await getProfile(apiBase, token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/profile',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          },
        }
      );
      expect(result).toEqual(mockProfile);
    });

    it('should handle request without token', async () => {
      const mockProfile: Profile = {
        consent_personalization: false,
        memory_paused: false,
        allergies: [],
        pregnancy_trimester: null,
        pregnancy_due_date: null,
        child_birthdate: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProfile,
      } as Response);

      await getProfile(apiBase);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/profile',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    });

    it('should throw error on failed request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => 'Unauthorized',
      } as Response);

      await expect(getProfile(apiBase, token)).rejects.toThrow('Unauthorized');
    });

    it('should throw error with status code when no error text', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => '',
      } as Response);

      await expect(getProfile(apiBase, token)).rejects.toThrow('HTTP 500');
    });
  });

  describe('putProfile', () => {
    it('should update profile successfully', async () => {
      const profileData: Profile = {
        consent_personalization: true,
        memory_paused: false,
        allergies: ['peanuts'],
        pregnancy_trimester: 1,
        pregnancy_due_date: '2025-09-15',
        child_birthdate: null,
      };

      const mockResponse = {
        ok: true,
        updated_at: '2025-09-24T20:30:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await putProfile(apiBase, profileData, token);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/profile',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
          },
          body: JSON.stringify(profileData),
        }
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle update without token', async () => {
      const profileData: Profile = {
        consent_personalization: false,
        memory_paused: true,
        allergies: [],
        pregnancy_trimester: null,
        pregnancy_due_date: null,
        child_birthdate: '2023-01-15',
      };

      const mockResponse = {
        ok: true,
        updated_at: '2025-09-24T20:30:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      await putProfile(apiBase, profileData);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/profile',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(profileData),
        }
      );
    });

    it('should throw error on failed update', async () => {
      const profileData: Profile = {
        consent_personalization: true,
        memory_paused: false,
        allergies: [],
        pregnancy_trimester: null,
        pregnancy_due_date: null,
        child_birthdate: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Bad Request',
      } as Response);

      await expect(putProfile(apiBase, profileData, token)).rejects.toThrow('Bad Request');
    });
  });
});

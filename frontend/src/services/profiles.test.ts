import { ProfilesService } from "./profiles";
import { ApiClient } from "./base";
import type { Profile } from "@/types/profile";

jest.mock("./base");

describe("ProfilesService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("ruft ApiClient.get mit korrektem Pfad auf", async () => {
    const mockProfiles: Profile[] = [
      {
        id: 1,
        name: "Test Profile",
        city: "Berlin",
        include_tax: true,
        default_tax_rate: 0.19,
      },
    ];

    (ApiClient.get as jest.Mock).mockResolvedValueOnce(mockProfiles);

    const result = await ProfilesService.list();

    expect(ApiClient.get).toHaveBeenCalledWith("/profiles/");
    expect(result).toEqual(mockProfiles);
  });

  it("propagiert Fehler von ApiClient", async () => {
    const error = new Error("Network error");
    (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);

    await expect(ProfilesService.list()).rejects.toThrow("Network error");
  });
});

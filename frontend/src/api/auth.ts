// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 26th, 2026
// Description: API module for authentication-related operations in the Gmail Cleaner frontend application.

// Import necessary modules and components
import { apiClient } from "./client";
import type {
  LoginResponse,
  CallbackRequest,
  CallbackResponse,
  MeResponse,
} from "../types";

// Define the authApi object that contains methods for authentication-related API calls
export const authApi = {
  // Method to get the login URL for initiating the authentication process
  getLoginUrl: () =>
    apiClient.get<LoginResponse>("/auth/login").then((r) => r.data),

  // Method to handle the callback from the authentication provider (exchanges the authorization code for a session token)
  callback: (body: CallbackRequest) =>
    apiClient
      .post<CallbackResponse>("/auth/callback", body)
      .then((r) => r.data),

  // Method to log out the user by invalidating the session token on the server
  logout: () => apiClient.post("/auth/logout").then(() => undefined),

  // Method to get the current authenticated user's information
  me: () => apiClient.get<MeResponse>("/auth/me").then((r) => r.data),
};

/**
 * Authentication types for EstimAI frontend
 */

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token: string;
  token_type: "bearer";
  user: {
    email: string;
    name: string;
  };
};

export type User = {
  email: string;
  name: string;
};

export type AuthState = {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
};

/** Shared between the settings Server Actions and the settings forms. */

export const DELETE_CONFIRMATION = "DELETE";

export interface TrackingState {
  granted: boolean;
  error: string | null;
}

export interface DeleteState {
  status: "idle" | "deleted" | "error";
  message: string | null;
}

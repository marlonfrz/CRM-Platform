export type ClientSummary = {
  id: string;
  name: string;
  address: string | null;
  created_at: string;
  updated_at: string;
};

export type ClientContact = {
  id: string;
  full_name: string;
  position: string | null;
  email: string | null;
  phone: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type Client = ClientSummary & {
  notes: string | null;
  contacts: ClientContact[];
};

export type AssignmentUser = {
  user_id: string;
  full_name: string;
  status: "ACTIVE" | "PENDING" | "DISABLED";
};

export type AssignmentTeam = {
  assigned: AssignmentUser[];
  available: AssignmentUser[];
};

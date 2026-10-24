export const IOC_TYPES = ["ipv4", "domain", "url", "md5", "sha1", "sha256"] as const;
export type IOCType = (typeof IOC_TYPES)[number];

export interface IOC {
  id: number;
  type: IOCType;
  value: string;
  raw_value: string;
  note: string | null;
  tags: string[];
  created_at: string;
}

export interface NewIOC {
  value: string;
  note?: string;
  tags: string[];
}

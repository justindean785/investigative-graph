import React from "react";
import {
  User,
  Mail,
  Smartphone,
  Globe,
  Network,
  AtSign,
  Building2,
  Wallet,
  MessageCircle,
  Link as LinkIcon,
  Fingerprint,
  MapPin,
} from "lucide-react";

export const ENTITY_TYPES = [
  { value: "person", label: "Person", color: "#06b6d4" },
  { value: "email", label: "Email", color: "#22d3ee" },
  { value: "phone", label: "Phone", color: "#f59e0b" },
  { value: "domain", label: "Domain", color: "#06b6d4" },
  { value: "ip", label: "IP Address", color: "#a78bfa" },
  { value: "username", label: "Username", color: "#22d3ee" },
  { value: "company", label: "Company", color: "#f59e0b" },
  { value: "wallet", label: "Wallet", color: "#fbbf24" },
  { value: "social", label: "Social Account", color: "#22d3ee" },
  { value: "url", label: "URL", color: "#06b6d4" },
  { value: "hash", label: "Hash", color: "#94a3b8" },
  { value: "location", label: "Location", color: "#10b981" },
];

export const ENTITY_KIND_ICONS = {
  person: User,
  email: Mail,
  phone: Smartphone,
  domain: Globe,
  ip: Network,
  username: AtSign,
  company: Building2,
  wallet: Wallet,
  social: MessageCircle,
  url: LinkIcon,
  hash: Fingerprint,
  location: Globe,
};

export function EntityKindIcon({
  kind,
  className = "w-4 h-4",
  strokeWidth = 1.5,
  style,
}) {
  const C = ENTITY_KIND_ICONS[kind] || Network;
  return (
    <C
      className={className}
      style={style}
      strokeWidth={strokeWidth}
      aria-hidden
    />
  );
}

export const RELATIONSHIP_TYPES = [
  { value: "owns", label: "Owns" },
  { value: "registered", label: "Registered" },
  { value: "resolves_to", label: "Resolves to" },
  { value: "used_on", label: "Used on" },
  { value: "interacts_with", label: "Interacts with" },
  { value: "linked_to", label: "Linked to" },
  { value: "employed_by", label: "Employed by" },
  { value: "located_at", label: "Located at" },
  { value: "transferred_to", label: "Transferred to" },
  { value: "associated_with", label: "Associated with" },
];

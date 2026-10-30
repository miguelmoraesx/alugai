import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep framework-generated assistant files out of the shared repository.
  agentRules: false,
};

export default nextConfig;

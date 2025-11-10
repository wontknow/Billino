#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */

/**
 * Environment Configuration Validator (Frontend)
 * Checks for missing or incorrectly configured environment variables.
 *
 * Usage:
 *     node scripts/check-env.js
 *     pnpm check-env
 */

const fs = require("fs");
const path = require("path");

// ============================================================================
// Configuration
// ============================================================================

const FRONTEND_ENV_REQUIRED = {
  NODE_ENV: {
    description: "Node environment (development/production)",
    allowedValues: ["development", "production"],
    default: "development",
  },
  NEXT_PUBLIC_API_URL: {
    description: "Backend API URL (must be accessible from browser)",
    allowedValues: null, // Any URL acceptable
    default: "http://127.0.0.1:8000",
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

function loadEnvFile(envPath) {
  /**Load environment variables from .env.local file.*/
  const envVars = {};

  if (!fs.existsSync(envPath)) {
    return envVars;
  }

  const content = fs.readFileSync(envPath, "utf-8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    // Skip comments and empty lines
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    // Parse KEY=VALUE
    if (trimmed.includes("=")) {
      const [key, ...valueParts] = trimmed.split("=");
      envVars[key.trim()] = valueParts.join("=").trim();
    }
  }

  return envVars;
}

function validateEnvVars(envVars, required, envFile) {
  /**Validate environment variables against requirements.*/
  const issues = [];

  for (const [key, config] of Object.entries(required)) {
    if (!(key in envVars)) {
      issues.push(
        `❌ Missing ${key} in ${envFile}\n` +
          `   Description: ${config.description}\n` +
          `   Default: ${config.default}`
      );
      continue;
    }

    const value = envVars[key];
    const allowed = config.allowedValues;

    // Validate against allowed values if specified
    if (allowed && !allowed.includes(value)) {
      issues.push(
        `⚠️  Invalid value for ${key} in ${envFile}\n` +
          `   Current: ${value}\n` +
          `   Allowed: ${allowed.join(", ")}`
      );
    }

    // Check for empty values
    if (!value) {
      issues.push(`❌ ${key} in ${envFile} is empty`);
    }
  }

  return [issues.length === 0, issues];
}

// ============================================================================
// Main Validation Logic
// ============================================================================

function checkFrontend(repoRoot) {
  /**Check frontend environment configuration.*/
  console.log("\n" + "=".repeat(70));
  console.log("🎨 FRONTEND ENVIRONMENT CHECK");
  console.log("=".repeat(70));

  const frontendPath = path.join(repoRoot, "frontend");
  const envFile = path.join(frontendPath, ".env.local");

  if (!fs.existsSync(envFile)) {
    console.log(`❌ No .env.local file found at ${envFile}`);
    console.log(`   Create one from .env.local.example:`);
    console.log(`   cp ${frontendPath}/.env.local.example ${frontendPath}/.env.local`);
    return false;
  }

  console.log(`✅ Found ${envFile}`);

  const envVars = loadEnvFile(envFile);
  const [isValid, issues] = validateEnvVars(envVars, FRONTEND_ENV_REQUIRED, ".env.local");

  if (isValid) {
    console.log("✅ All required variables are set correctly");
    console.log("\nConfiguration:");
    for (const [key, config] of Object.entries(FRONTEND_ENV_REQUIRED)) {
      const value = envVars[key] || config.default;
      console.log(`  - ${key}: ${value}`);
    }
    return true;
  } else {
    console.log("❌ Configuration issues found:\n");
    for (const issue of issues) {
      console.log(`  ${issue}\n`);
    }
    return false;
  }
}

function main() {
  /**Main entry point.*/
  const repoRoot = path.dirname(path.dirname(__dirname));

  // Parse CLI arguments
  if (process.argv.length > 2) {
    const arg = process.argv[2];
    if (arg === "--help" || arg === "-h") {
      console.log(
        "Environment Configuration Validator (Frontend)\n" +
          "Usage: node scripts/check-env.js\n" +
          "       pnpm check-env"
      );
      process.exit(0);
    } else {
      console.log(`Unknown argument: ${arg}`);
      process.exit(1);
    }
  }

  // Run checks
  const frontendOk = checkFrontend(repoRoot);

  // Summary
  console.log("\n" + "=".repeat(70));
  console.log("📋 SUMMARY");
  console.log("=".repeat(70));

  if (frontendOk) {
    console.log("✅ Frontend environment configuration is valid!");
    console.log("\n🚀 You can now start development:");
    console.log("   pnpm dev");
    process.exit(0);
  } else {
    console.log("❌ Fix the issues above before continuing");
    process.exit(1);
  }
}

main();

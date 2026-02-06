# GitHub Copilot Instructions for Billino

## Repository Overview

Billino is an **over-engineered, offline-capable invoicing application** with clean FE/BE separation, designed for small businesses in Germany. The project follows German tax law compliance (§14 UStG) and is built with a modern tech stack:

- **Backend**: FastAPI + SQLite + SQLModel (Python 3.11+)
- **Frontend**: Next.js 16 (App Router) + React 19 + shadcn/ui + Tailwind CSS v4 + TypeScript
- **Desktop**: Electron (with bundled FastAPI backend)
- **Database**: SQLite with Foreign Key constraints
- **PDF Generation**: ReportLab (A4 and A6 formats)

## Architecture Principles

### SOLID Principles

1. **Single Responsibility Principle (SRP)**
   - Each service class should handle one specific business concern
   - Routers handle HTTP concerns only, delegate business logic to services
   - Models define data structures only, no business logic

2. **Open/Closed Principle (OCP)**
   - Use dependency injection for extensibility
   - Design services to be extended through configuration, not modification
   - Use SQLModel for flexible schema extensions

3. **Liskov Substitution Principle (LSP)**
   - Maintain consistent interfaces across similar services
   - Ensure derived models can replace base models without breaking behavior

4. **Interface Segregation Principle (ISP)**
   - Keep API endpoints focused and specific
   - Split large DTOs into focused request/response models
   - Use separate read/create models (e.g., `InvoiceRead`, `InvoiceCreate`)

5. **Dependency Inversion Principle (DIP)**
   - Depend on abstractions (SQLModel Session) not concrete implementations
   - Use FastAPI's dependency injection (`Depends(get_session)`)
   - Services should be injected, not instantiated directly in routes

### Clean Code Practices

#### Naming Conventions
- **Python (Backend)**:
  - Classes: `PascalCase` (e.g., `InvoiceNumberGenerator`)
  - Functions/methods: `snake_case` (e.g., `generate_next_invoice_number`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TAX_RATE`)
  - Private members: prefix with `_` (e.g., `_calculate_tax`)

- **TypeScript (Frontend)**:
  - Components: `PascalCase` (e.g., `CustomersTable`)
  - Files: Match component name (e.g., `CustomersTable.tsx`)
  - Functions: `camelCase` (e.g., `fetchCustomers`)
  - Constants: `UPPER_SNAKE_CASE` for true constants
  - Types/Interfaces: `PascalCase` (e.g., `Customer`, `InvoiceFormData`)

#### Code Organization

**Backend Structure:**
```
backend/
├── models/          # SQLModel data models (table=True) + DTOs
├── routers/         # FastAPI route handlers (thin layer)
├── services/        # Business logic (thick layer)
├── utils/           # Shared utilities (logger, helpers)
└── tests/           # pytest tests
```

**Frontend Structure:**
```
frontend/src/
├── app/             # Next.js App Router (pages + layouts)
├── components/ui/   # shadcn/ui primitives (reusable)
├── features/        # Feature-specific presentational components
├── services/        # API client services
└── types/           # Shared TypeScript types
```

#### Function and Method Design
- **Keep functions small**: Max 20-30 lines per function
- **Single purpose**: Each function should do one thing well
- **Descriptive names**: Use verb-noun combinations (e.g., `calculate_total_tax`, `fetch_invoice_by_id`)
- **Avoid side effects**: Pure functions when possible
- **Error handling**: Always validate inputs and handle edge cases

#### Comments and Documentation
- **Python**: Use docstrings for all public functions/classes
  - Include Args, Returns, Raises sections
  - Explain complex business logic with inline comments
  - Reference German tax law where relevant (e.g., "§14 UStG compliance")

- **TypeScript**: Use JSDoc for complex functions
  - Avoid obvious comments ("// increment counter")
  - Document non-obvious business rules
  - Explain "why" not "what" in comments

## Backend Development Standards

### FastAPI Patterns

#### Router Structure
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Customer
from utils import logger

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=Customer, status_code=201)
def create_customer(customer: Customer, session: Session = Depends(get_session)):
    """
    Create a new customer.
    
    **Request Body:**
    - name (string, required): Customer name
    - address (string, optional): Customer address
    - city (string, optional): Customer city
    
    **Returns:**
    - Customer object with assigned ID
    """
    logger.debug(f"➕ POST /customers - Creating customer: {customer.name}")
    
    if not customer.name:
        logger.error("❌ Customer name is missing")
        raise HTTPException(status_code=400, detail="Name is required")
    
    session.add(customer)
    session.commit()
    session.refresh(customer)
    
    logger.info(f"✅ Customer created: ID={customer.id}")
    return customer
```

**Key Patterns:**
- Use `Depends(get_session)` for DB sessions
- Include comprehensive docstrings with examples
- Log significant operations with emoji prefixes (➕ ✅ ❌ 🔍)
- Return appropriate HTTP status codes (201 for create, 200 for read)
- Always commit and refresh for create/update operations

#### Service Layer Pattern
```python
from sqlmodel import Session, select
from models import Invoice

def generate_next_invoice_number(session: Session) -> str:
    """
    Generate the next invoice number globally.
    
    Format: "YY | NNN" where YY is current year and NNN is sequential number.
    
    IMPORTANT: German tax law (§14 UStG) requires invoice numbers to be
    unique and sequential across the entire business.
    
    Args:
        session: Database session
    
    Returns:
        Next invoice number in format "YY | NNN"
    """
    # Implementation...
    pass
```

**Service Guidelines:**
- Keep business logic in services, not routers
- Services should be pure functions when possible
- Use type hints for all parameters and return values
- Document legal/business requirements

### Database and Models

#### SQLModel Patterns
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
```

**Model Guidelines:**
- Use `Optional[int]` with `default=None` for auto-increment IDs
- Use `Optional[str] = None` for nullable fields
- Keep models simple - no business logic
- Use separate Create/Read models when needed (e.g., `InvoiceCreate`, `InvoiceRead`)

### Testing Standards

#### Test Structure (pytest)
```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

def test_create_customer_success(client: TestClient, session: Session):
    """Test successful customer creation"""
    response = client.post(
        "/customers/",
        json={"name": "John Doe", "address": "123 Main St", "city": "Berlin"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["id"] is not None
```

**Testing Requirements:**
- Write tests for all new features and bug fixes
- Use descriptive test names (test_[action]_[expected_outcome])
- Test happy path, edge cases, and error conditions
- Aim for 85%+ code coverage
- Use fixtures for common setup
- Mock external dependencies when appropriate

### Code Formatting and Linting

**Python Tools:**
- `black`: Auto-formatter (line length 88)
- `isort`: Import sorting
- Pre-commit hooks enforce formatting

**Run before committing:**
```bash
cd backend
black .
isort .
pytest --cov=.
```

## Frontend Development Standards

### React and Next.js Patterns

#### Component Structure
```typescript
"use client";

import type React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Customer } from "@/types/customer";

type Props = {
  customers: Customer[];
  emptyMessage?: React.ReactNode;
};

export function CustomersTable({ customers, emptyMessage }: Props) {
  const hasData = customers.length > 0;
  
  return (
    <Card className="w-full mx-auto">
      <CardHeader>
        <CardTitle>Kunden</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Component implementation */}
      </CardContent>
    </Card>
  );
}
```

**Component Guidelines:**
- Use TypeScript strict mode - no `any` types
- Define Props type for all components
- Use `type` instead of `interface` for consistency
- Prefer function components over class components
- Use React 19 features (use client/server directives)
- Keep components focused and single-purpose

#### State Management
- Use React hooks (`useState`, `useEffect`, `useCallback`)
- Prefer server components when no interactivity needed
- Use "use client" directive only when necessary
- Avoid prop drilling - lift state appropriately

#### Next.js App Router Patterns
```typescript
// app/(shell)/customers/page.tsx
import { CustomersController } from "./CustomersController";

export default function CustomersPage() {
  return <CustomersController />;
}

// app/(shell)/customers/CustomersController.tsx
import { CustomersTable } from "@/features/customers/CustomersTable";
import { fetchCustomers } from "@/services/customers";

export async function CustomersController() {
  const customers = await fetchCustomers();
  return <CustomersTable customers={customers} />;
}
```

**App Router Guidelines:**
- Use Server Components by default
- Page files should be thin - delegate to Controllers
- Controllers handle data orchestration
- Features contain presentational components
- Services handle API calls

### Styling with Tailwind CSS v4

**Styling Standards:**
- Use Tailwind utility classes, avoid custom CSS when possible
- Use shadcn/ui components for consistent design
- Follow responsive design patterns (mobile-first)
- Use semantic class names in custom components
- Leverage CSS variables for theming

**Example:**
```typescript
<Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl">
```

### API Service Pattern

```typescript
// src/services/base.ts
export class ApiClient {
  static baseUrl(): string {
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }

  static async get<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${this.baseUrl()}${path}`;
    const response = await fetch(url, init);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    
    return response.json();
  }
}
```

**API Guidelines:**
- Centralize API calls in service files
- Use TypeScript generics for type-safe responses
- Handle errors gracefully
- Use environment variables for API URLs

### Testing Standards (Frontend)

**Jest + React Testing Library:**
```typescript
import { render, screen } from "@testing-library/react";
import { CustomersTable } from "./CustomersTable";

describe("CustomersTable", () => {
  it("renders customer data correctly", () => {
    const customers = [
      { id: 1, name: "John Doe", address: "123 Main St", city: "Berlin" }
    ];
    
    render(<CustomersTable customers={customers} />);
    
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });
  
  it("shows empty message when no customers", () => {
    render(<CustomersTable customers={[]} />);
    expect(screen.getByText("Keine Kunden gefunden")).toBeInTheDocument();
  });
});
```

**Testing Requirements:**
- Test component rendering and user interactions
- Use semantic queries (`getByRole`, `getByText`)
- Test error states and edge cases
- Keep tests focused and isolated

### Code Formatting and Linting

**TypeScript Tools:**
- `prettier`: Code formatting
- `eslint`: Linting (ESLint 9 + Next.js config)
- TypeScript strict mode enabled

**Run before committing:**
```bash
cd frontend
pnpm format
pnpm lint
pnpm typecheck
pnpm test
```

## Security Best Practices

### Backend Security
- Never commit secrets (use `.env` files, excluded in `.gitignore`)
- Validate all user inputs with Pydantic/SQLModel
- Use parameterized queries (SQLModel handles this)
- Implement proper CORS configuration (controlled via `.env`)
- Log security-relevant events
- Use HTTPS in production

### Frontend Security
- Sanitize user inputs before rendering
- Use environment variables for API URLs (`NEXT_PUBLIC_*`)
- Never expose API keys in client-side code
- Validate data from API responses
- Use TypeScript for type safety

## Documentation Standards

### Code Documentation
- **README.md**: Keep comprehensive and up-to-date
- **Docstrings/JSDoc**: Document all public APIs
- **Inline comments**: Explain complex business logic
- **API docs**: FastAPI generates OpenAPI docs automatically

### Commit Messages
Follow conventional commits format:
```
feat: add customer search functionality
fix: resolve invoice number generation bug
docs: update API documentation
test: add tests for PDF generation
refactor: simplify tax calculation logic
```

### Pull Request Template
- Use the existing PR template in `.github/PULL_REQUEST_TEMPLATE.md`
- Include description of changes
- Reference related issues
- List testing performed
- Note any breaking changes

## Environment Configuration

### Backend Environment Variables
```bash
# backend/.env
ENV=development              # or: production
LOG_LEVEL=DEBUG              # or: INFO
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend Environment Variables
```bash
# frontend/.env.local
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

**Important:**
- Never commit `.env` files
- Use `.env.example` files as templates
- Validate environment variables on startup
- Use `NEXT_PUBLIC_*` prefix for browser-accessible variables

## Logging Standards

### Backend Logging
```python
from utils import logger

logger.debug("🔍 Detailed debug information")
logger.info("✅ Important events")
logger.warning("⚠️ Warning messages")
logger.error("❌ Error occurred")
```

**Logging Guidelines:**
- Use emoji prefixes for visual scanning
- Log at appropriate levels (DEBUG in dev, INFO in prod)
- Include context (IDs, names, values)
- Avoid logging sensitive data
- Use structured logging when possible

### Frontend Logging
```typescript
console.log("✅ [Service] Customer fetched:", customer);
console.error("❌ [API] Failed to fetch:", error);
```

## German Tax Law Compliance

### Invoice Numbers (§14 UStG)
- Must be sequential and gap-free
- Global across all profiles/customers
- Format: "YY | NNN" (e.g., "25 | 001")
- Never reuse or skip numbers

### Tax Calculations
- Support 0% (§19 UStG - Kleinunternehmer)
- Support 19% (standard VAT)
- Support 7% (reduced VAT)
- Handle both gross and net amounts
- Calculate tax correctly: `tax = gross - (gross / (1 + tax_rate))`

## Development Workflow

### Before Starting Work
1. Pull latest changes from `main`
2. Create feature branch: `feature/description` or `fix/description`
3. Check environment setup: `python scripts/check_env.py` and `pnpm check-env`

### During Development
1. Write code following these guidelines
2. Write tests for new functionality
3. Run linters and formatters
4. Commit frequently with descriptive messages
5. Keep changes focused and atomic

### Before Pushing
1. Run full test suite (backend and frontend)
2. Check code coverage
3. Ensure all linters pass
4. Update documentation if needed
5. Create pull request using template

### CI/CD Pipeline
- GitHub Actions run on all PRs
- Backend tests with pytest
- Frontend tests with Jest
- Linting checks (black, isort, eslint, prettier)
- Type checking (TypeScript)
- All checks must pass before merge

## Common Patterns and Anti-Patterns

### ✅ DO
- Use dependency injection
- Write comprehensive tests
- Follow SOLID principles
- Use type hints/types everywhere
- Log important operations
- Handle errors gracefully
- Keep functions small and focused
- Use descriptive variable names
- Document complex logic

### ❌ DON'T
- Hard-code configuration values
- Use `any` type in TypeScript
- Ignore linter warnings
- Skip writing tests
- Commit commented-out code
- Use magic numbers/strings
- Create God classes/functions
- Mix business logic with HTTP handling
- Ignore error cases

## Additional Resources

### Documentation
- FastAPI: https://fastapi.tiangolo.com
- SQLModel: https://sqlmodel.tiangolo.com
- Next.js: https://nextjs.org/docs/app
- shadcn/ui: https://ui.shadcn.com
- Tailwind CSS: https://tailwindcss.com/docs

### Testing
- pytest: https://docs.pytest.org/
- React Testing Library: https://testing-library.com/docs/react-testing-library/intro/

### Code Quality
- SOLID Principles: https://en.wikipedia.org/wiki/SOLID
- Clean Code: Robert C. Martin's principles
- Python PEP 8: https://pep8.org/
- TypeScript Guidelines: https://www.typescriptlang.org/docs/handbook/

## Summary

When contributing to Billino:
1. **Follow SOLID principles** - Keep code modular and maintainable
2. **Write clean, readable code** - Future you will thank you
3. **Test everything** - Aim for high coverage
4. **Document thoroughly** - Explain complex business logic
5. **Respect the architecture** - Routers → Services → Models
6. **Use the tools** - Linters, formatters, type checkers
7. **Think about security** - Validate inputs, protect secrets
8. **Comply with regulations** - German tax law (§14 UStG)

**Happy coding! 🚀**

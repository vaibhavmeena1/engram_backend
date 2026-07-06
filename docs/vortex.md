# Vortex Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [What is Vortex?](#what-is-vortex)
3. [Why Vortex?](#why-vortex)
4. [Key Features](#key-features)
5. [Architecture Overview](#architecture-overview)
6. [Getting Started](#getting-started)
7. [Core Components](#core-components)
8. [Configuration](#configuration)
9. [Examples & Use Cases](#examples--use-cases)
10. [Best Practices](#best-practices)
11. [Integrations](#integrations)
12. [Development & Testing](#development--testing)
13. [CLI Tools](#cli-tools)

---

## Introduction

Vortex is a modern FastAPI wrapper library designed to accelerate the development of production-ready microservices. Inspired by Torpedo (a similar wrapper for Sanic), Vortex provides a structured, opinionated approach to building FastAPI applications with enterprise-grade features out of the box.

## What is Vortex?

Vortex is a **FastAPI wrapper and enhancement framework** that:

- **Abstracts common microservice patterns** into reusable components
- **Provides pre-configured integrations** for monitoring, logging, and error tracking
- **Standardizes application structure** for consistent development practices  
- **Simplifies configuration management** through environment-driven setup
- **Accelerates development** by reducing boilerplate code

### Core Philosophy

Vortex follows the principle of "convention over configuration" - providing sensible defaults while maintaining the flexibility to customize when needed. It's designed for teams building multiple microservices who want consistency, maintainability, and rapid development cycles.

## Why Vortex?

### Problems Vortex Solves

1. **Boilerplate Reduction**: Eliminates repetitive FastAPI setup code across multiple services
2. **Configuration Management**: Provides structured, environment-aware configuration handling
3. **Monitoring Integration**: Built-in APM and error tracking without manual setup
4. **Logging Standardization**: Consistent, structured logging across all services
5. **Development Speed**: Get from idea to running service in minutes, not hours
6. **Production Readiness**: Includes health checks, error handling, and observability by default

### Benefits Over Plain FastAPI

| Feature | Plain FastAPI | Vortex |
|---------|---------------|---------|
| Setup Time | Manual configuration required | Instant with sensible defaults |
| Health Checks | Manual implementation | Built-in endpoints |
| Error Handling | Custom exception handlers | Pre-configured global handlers |
| APM Integration | Manual setup (Elastic APM, Sentry) | Automatic configuration |
| Logging | Basic Python logging | Structured logging with metadata |
| Middleware | Manual registration | Pre-configured common middleware |
| Configuration | Manual environment handling | Structured config management |

## Key Features

### ðŸš€ **Rapid Development**
- Zero-configuration startup for standard use cases
- Pre-built routers for common functionality
- Automatic health check endpoints

### ðŸ—ï¸ **Enterprise Architecture**
- Structured project organization
- Standardized error handling
- Built-in middleware stack

### ðŸ“Š **Observability**
- **Elastic APM Integration**: Performance monitoring out of the box
- **Sentry Error Tracking**: Automatic error capture and reporting
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Rich Console Output**: Beautiful development-time logging

### ðŸ›¡ï¸ **Production Ready**
- Comprehensive error handling with custom exception registry
- Environment-aware configuration management
- Built-in security headers and CORS handling
- Request correlation tracking

### ðŸ”§ **Developer Experience**
- Rich terminal output during development
- Hot reload support
- Comprehensive type hints
- Extensive configuration options

## Architecture Overview

Vortex follows a layered architecture pattern:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                 Application Layer                â”‚
â”‚              (Your Business Logic)              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                  Vortex Layer                   â”‚
â”‚         (Middleware, Routing, Config)           â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                 FastAPI Layer                   â”‚
â”‚            (HTTP Handling, OpenAPI)             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                 ASGI Layer                      â”‚
â”‚             (Uvicorn, Hypercorn)               â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Core Components

1. **Vortex Core** (`vortex.py`): Main application wrapper
2. **Configuration System** (`config/`): Environment-driven configuration
3. **Router Management** (`defaults/`): Automatic router registration
4. **Middleware Stack** (`middleware.py`): Pre-configured middleware
5. **Error Handling** (`error_handling/`): Centralized exception management
6. **Integrations** (`integrations/`): APM, logging, and monitoring
7. **Lifespan Management** (`lifespan.py`): Startup/shutdown lifecycle hooks

## Getting Started

### Installation

```bash
# Using pip
pip install vortex

# Using Poetry (recommended for development)
poetry add vortex
```

### Basic Usage

```python
from vortex import Vortex
from fastapi import APIRouter

# Create your router
api_router = APIRouter()

@api_router.get("/hello")
async def hello_world():
    return {"message": "Hello, World!"}

# Create Vortex application
app = Vortex(
    title="My Microservice",
    routers=[api_router]
)

# Get the FastAPI app
fastapi_app = app.create_app()

if __name__ == "__main__":
    app.run()  # Uses uvicorn internally
```

### Quick Start with Configuration

```python
from vortex import Vortex

# Create with environment-based configuration
vortex = Vortex(
    title="User Service",
    debug=True,  # Will be overridden by config
    service_config={
        "NAME": "user-service",
        "HOST": "0.0.0.0",
        "PORT": 8080,
        "DEBUG": False
    }
)

app = vortex.create_app()
```

## Core Components

### 1. Vortex Application Class

The main `Vortex` class is the entry point for all applications:

```python
class Vortex:
    def __init__(
        self,
        routers: List[APIRouter] | None = None,
        lifespans: List[LifespanTuple] | None = None,
        service_config: Dict[str, Any] | None = None,
        middlewares: List[MiddlewareTuple] | None = None,
        debug: bool = False,
        **vortex_kwargs
    ):
```

### 2. Router Management

Vortex provides flexible router registration:

```python
# Method 1: During initialization
vortex = Vortex(routers=[users_router, products_router])

# Method 2: Dynamic registration
vortex = Vortex()
vortex.register_router(users_router)
vortex.register_router(products_router)
```

### 3. Lifespan Events

Manage application lifecycle with startup/shutdown hooks:

```python
async def startup_handler():
    print("Application starting up...")

async def shutdown_handler():
    print("Application shutting down...")

vortex = Vortex(
    lifespans=[
        (startup_handler, "startup"),
        (shutdown_handler, "shutdown")
    ]
)
```

### 4. Middleware System

Pre-configured middleware stack with priority ordering:

```python
# Custom middleware
from vortex.middleware import MiddlewareTuple

custom_middlewares = [
    MiddlewareTuple(MyCustomMiddleware, {"priority": 1}),
    MiddlewareTuple(AnotherMiddleware, {"priority": 2})
]

vortex = Vortex(middlewares=custom_middlewares)
```

### 5. Error Handling

Centralized exception management:

```python
from vortex.error_handling import ErrorHandler, ExceptionRegistry

# Custom error handler
class CustomErrorHandler(ErrorHandler):
    async def handle_custom_error(self, request, exc):
        return {"error": "Custom handling"}

vortex = Vortex(error_handler=CustomErrorHandler())
```

## Configuration

Vortex uses a hierarchical configuration system:

1. **Default Configuration**: Sensible defaults for all settings
2. **Environment Variables**: Override defaults with environment-specific values
3. **Configuration Files**: JSON/YAML configuration files
4. **Runtime Configuration**: Programmatic configuration during initialization

### Environment Variables

```bash
# Core settings
VORTEX_NAME=my-service
VORTEX_HOST=0.0.0.0
VORTEX_PORT=8000
VORTEX_DEBUG=false

# Logging
VORTEX_ACCESS_LOG=true
VORTEX_DEV_MODE=false

# Integrations
SENTRY_DSN=your-sentry-dsn
ELASTIC_APM_SERVICE_NAME=my-service
```

### Configuration File

```json
{
  "NAME": "user-service",
  "HOST": "0.0.0.0", 
  "PORT": 8080,
  "DEBUG": false,
  "ACCESS_LOG": true,
  "WORKERS": 1,
  "sentry": {
    "dsn": "your-sentry-dsn",
    "environment": "production"
  },
  "elastic_apm": {
    "service_name": "user-service",
    "server_url": "http://apm-server:8200"
  }
}
```

## Examples & Use Cases

### Multi-Router Application

```python
from fastapi import APIRouter
from vortex import Vortex

# Create domain-specific routers
users_router = APIRouter(prefix="/users", tags=["users"])
products_router = APIRouter(prefix="/products", tags=["products"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

@users_router.get("/")
async def get_users():
    return {"users": []}

@products_router.get("/")
async def get_products():
    return {"products": []}

# Initialize with multiple routers
vortex = Vortex(
    title="E-commerce API",
    routers=[users_router, products_router, admin_router]
)

app = vortex.create_app()
```

### Configuration-Driven Service

```python
from vortex import Vortex, CONFIG

# Configuration loaded from environment or config file
vortex = Vortex(
    service_config=CONFIG.config,  # Automatically loaded
    title=CONFIG.config.get("NAME", "Default Service")
)

app = vortex.create_app()
```

### Custom Lifespan Management

```python
import asyncio
from vortex import Vortex

async def setup_database():
    """Initialize database connections"""
    print("Setting up database...")

async def setup_cache():
    """Initialize Redis cache"""
    print("Setting up cache...")

async def cleanup_resources():
    """Clean up resources on shutdown"""
    print("Cleaning up resources...")

vortex = Vortex(
    lifespans=[
        (setup_database, "startup"),
        (setup_cache, "startup"), 
        (cleanup_resources, "shutdown")
    ]
)

app = vortex.create_app()
```

## Best Practices

### 1. Project Structure

Organize your Vortex projects consistently:

```
your-service/
â”œâ”€â”€ main.py                 # Application entry point
â”œâ”€â”€ config.json             # Configuration file
â”œâ”€â”€ routers/               
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ users.py           # User-related endpoints
â”‚   â”œâ”€â”€ products.py        # Product-related endpoints
â”‚   â””â”€â”€ health.py          # Custom health checks
â”œâ”€â”€ services/              
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ user_service.py    # Business logic
â”‚   â””â”€â”€ product_service.py
â”œâ”€â”€ models/                
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ user.py           # Pydantic models
â”‚   â””â”€â”€ product.py
â””â”€â”€ tests/
    â”œâ”€â”€ test_routers.py
    â””â”€â”€ test_services.py
```

### 2. Router Organization

Keep routers focused on specific domains:

```python
# users.py
users_router = APIRouter(prefix="/api/v1/users", tags=["users"])

@users_router.get("/", response_model=List[User])
async def list_users():
    return await user_service.get_all_users()

@users_router.post("/", response_model=User)
async def create_user(user: CreateUserRequest):
    return await user_service.create_user(user)
```

### 3. Configuration Management

Use environment-specific configurations:

```python
# Use configuration classes
from vortex.config import HostConfig

config = HostConfig.from_env()
vortex = Vortex(service_config=config.to_dict())
```

### 4. Error Handling

Implement domain-specific error handlers:

```python
from vortex.exceptions import VortexException

class UserNotFoundError(VortexException):
    pass

@users_router.get("/{user_id}")
async def get_user(user_id: int):
    user = await user_service.get_user(user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    return user
```

## Integrations

### Elastic APM

Automatic performance monitoring:

```json
{
  "elastic_apm": {
    "service_name": "my-service",
    "server_url": "http://apm-server:8200",
    "environment": "production"
  }
}
```

### Sentry Error Tracking

Automatic error capture:

```json
{
  "sentry": {
    "dsn": "your-sentry-dsn",
    "environment": "production",
    "traces_sample_rate": 0.1
  }
}
```

### Structured Logging

Rich development experience with structured production logs:

```python
from vortex.logging.log import logger

logger.info("User created", extra={"user_id": 123, "email": "user@example.com"})
```

## Development & Testing

### Setting Up Development Environment

```bash
# Clone and setup
git clone <your-vortex-service>
cd your-vortex-service

# Install dependencies
poetry install

# Run in development mode
export VORTEX_DEBUG=true
export VORTEX_DEV_MODE=true
python main.py
```


### Performance Considerations

1. **Connection Pooling**: Use async database clients
2. **Middleware Order**: Place performance-critical middleware first
3. **Logging Level**: Use appropriate log levels in production
4. **APM Sampling**: Configure sampling rates for performance monitoring

## CLI Tools

Vortex provides powerful command-line tools to enhance your development workflow. The CLI is available through the `vortex` command after installation.

### Installation & Setup

The CLI is automatically available after installing Vortex:

```bash
# Install Vortex (CLI included)
pip install vortex

# Verify CLI installation
vortex --help
```

### Interactive Console

The `vortex console` command provides a Rails-like interactive console with your FastAPI application pre-loaded, including all lifespan hooks and dependencies.

#### Basic Usage

```bash
# Navigate to your project directory
cd your-vortex-project/

# Start the interactive console
vortex console
```

#### Configuration

The console automatically detects your application using environment variables:

```bash
# Set custom paths (optional)
export VORTEX_APP="app.main:app"        # Path to your FastAPI app instance
export VORTEX_MANAGER="app.main:vortex" # Path to your Vortex manager instance

# Start console with custom configuration
vortex console
```

#### Console Features

- **Pre-loaded Application**: Your FastAPI app and Vortex manager are automatically available
- **Lifespan Support**: Startup hooks run automatically, shutdown hooks run on exit
- **Async/Await Support**: Full support for top-level `await` operations
- **Model Auto-import**: Database models are automatically imported if available
- **Rich Environment**: Built-in imports for common modules (`json`, `os`, `sys`, `asyncio`)

#### Example Console Session

```python
ðŸŽ¯ FastAPI Console Ready!
============================================================
Available objects:
  â€¢ app: FastAPI
  â€¢ vortex_manager: Vortex
  â€¢ asyncio: module
  â€¢ json: module
  â€¢ os: module
  â€¢ sys: module

ðŸ’¡ You can use 'await' for async operations!
ðŸ’¡ Type 'exit()' or Ctrl+D to quit
============================================================

# Make async requests
>>> response = await app.test_client().get("/api/users")
>>> print(response.json())

# Access your models and services directly
>>> users = await UserService.get_all()
>>> print(f"Total users: {len(users)}")

# Test database connections
>>> await db.execute("SELECT 1")

# Exit the console
>>> exit()
ðŸ›‘ Cleaning up console environment...
âœ… Console cleanup completed!
```

#### Requirements

The console requires IPython for the interactive shell:

```bash
# IPython is included with Vortex by default
# But if you need to install it separately:
pip install ipython

## Conclusion

Vortex transforms FastAPI development from a manual, configuration-heavy process into a streamlined, convention-driven experience. By providing enterprise-grade features out of the box while maintaining FastAPI's flexibility, Vortex enables teams to build production-ready microservices faster and more consistently.

Whether you're building a single service or a complex microservices architecture, Vortex provides the foundation, tools, and patterns needed for success.

---

*For more examples and advanced usage patterns, see the `examples/` directory in the Vortex repository.*
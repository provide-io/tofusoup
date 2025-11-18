# Glossary

Definitions of terms used in TofuSoup and the Terraform ecosystem.

## A

**Attribute**
: A named field in a Terraform resource, data source, or provider schema.

## C

**Conformance Test**
: A test that verifies an implementation correctly follows a specification, ensuring cross-language compatibility.

**CTY (Configuration Type)**
: Terraform's type system for configuration values. Includes primitives (string, number, bool), collections (list, map, set), and structural types (object, tuple).

## D

**Data Source**
: A Terraform component that reads external data for use in configurations. Read-only resource.

**Dynamic Type**
: A CTY type that can hold any value type. Used when the type isn't known until runtime.

## H

**Harness**
: A test harness is a reference implementation used for compatibility testing. TofuSoup includes Go harnesses.

**HCL (HashiCorp Configuration Language)**
: The configuration language used by Terraform. Combines declarative resource definitions with expressions.

## M

**Matrix Testing**
: Testing a provider or configuration across multiple versions of Terraform/OpenTofu simultaneously.

**MessagePack**
: Binary serialization format used in Terraform's wire protocol. More compact than JSON.

## O

**OpenTofu**
: Open-source fork of Terraform maintained by the Linux Foundation. API-compatible with Terraform 1.5.x.

## P

**Provider**
: A Terraform plugin that manages resources for a specific service or platform (AWS, Azure, etc.).

**Pyvider**
: Python framework for building Terraform providers. Part of the provide.io ecosystem.

## R

**Resource**
: A Terraform component representing infrastructure that can be created, updated, and destroyed.

**RPC (Remote Procedure Call)**
: Communication protocol used between Terraform and providers. Uses gRPC in protocol version 6+.

## S

**Schema**
: Definition of attributes, blocks, and behaviors for a provider, resource, or data source.

**Stir**
: TofuSoup's matrix testing framework for running tests across multiple tool versions.

## T

**Terraform**
: Infrastructure-as-code tool by HashiCorp. Provisions and manages cloud resources using declarative configuration.

**Test Suite**
: Collection of related conformance tests (e.g., CTY suite, RPC suite, wire protocol suite).

**TofuSoup**
: Cross-language conformance testing framework for the Terraform ecosystem. The tool you're using now!

## U

**Unknown Value**
: A CTY value whose actual value isn't known yet (typically during `terraform plan`). Different from null.

## W

**Wire Protocol**
: Binary protocol for communication between Terraform and providers. Uses MessagePack + Base64 encoding.

**Workenv**
: Workspace environment manager for handling multiple Terraform/OpenTofu versions.

## Related Resources

- [Core Concepts](core-concepts/architecture/)
- [What is TofuSoup?](getting-started/what-is-tofusoup/)
- [FAQ](faq/)
- [Terraform Glossary](https://www.terraform.io/docs/glossary)

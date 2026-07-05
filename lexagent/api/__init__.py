"""HTTP API surface for LexAgent.

A thin wrapper over the analysis graph: request/response schemas, per-endpoint
handlers, and a single Lambda entry point that routes with aws-lambda-powertools.
The graph itself is untouched — these handlers only marshal inputs and outputs.
"""

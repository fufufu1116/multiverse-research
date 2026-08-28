# Phase C v17 recovery direction

Status: DRAFT / REVIEW ONLY / NOT AUTHORIZED. Runtime: OFF.

Binding: canonical main 74ea95e59ac0654e1a0c1f811a178b3eef7b073c; predecessor PR74 head 0e3b062e9ab4e68c5a3ae6382845da4d5ef871e7; incident closure comment 5453315135; prior receipt 5452575750 is consumed.

Goal: reduce iPhone operator work by replacing the Step1 INIT, thirteen chunk entries, assembly and source verification with one independently reviewed exact single-paste Step1 transport action.

The implementation must be derived from Fresh-fetched reviewed repository artifacts and authoritative manifest comment 5420731105. It must preserve the reviewed Step1 payload invariants: decoded 4687 bytes with SHA-256 bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74; RFC4648 base64 6252 characters with SHA-256 f7c353761edf26a0ddeb25a129a7b152a16cf587bf5b620b6421863aa25418b2; thirteen authoritative chunks.

Before future live delivery, Core must Fresh-fetch the independently reviewed complete action and mechanically verify its complete hash. No command variant may be selected or reconstructed from chat history.

Required gates before any new live session: exact implementation freeze, Independent Lab review, Independent Auditor review, Owner presentation, explicit Owner approval, new one-shot receipt.

No new Codespace, OAuth, authenticated probe, production apply, production mutation, main/ruleset mutation, secret operation, merge, or Runtime activation is authorized by this note.
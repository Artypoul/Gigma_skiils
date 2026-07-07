# Agent classes

The main skill maps execution to agent classes: SourceIntakeAgent, DecodeAgent, TreeDiscoveryAgent, RectTargetAgent, LayoutTransferAgent, ViewportValidationAgent, AssetAgent, PaintValidationAgent, LiveCompareAgent, BehaviorDiscoveryAgent, InteractionAgent, BehaviorValidationAgent, LivenessDiscoveryAgent, MotionTraceAgent, LivenessValidationAgent and OutputContractAgent.


## v1.7 liveness agents

- `LivenessDiscoveryAgent`: detects animations, transitions, scroll-linked effects, canvas, WebGL, video and runtime libraries.
- `MotionTraceAgent`: captures original and candidate frame samples, computed styles, transforms, canvas hashes and optional video.
- `LivenessValidationAgent`: compares runtime traces and fails static clones of dynamic content.

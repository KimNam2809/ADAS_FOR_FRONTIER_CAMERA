# RoadWatch evaluation assets

The runtime package keeps the evaluation code, schemas, and small gate reports in Git.
Large review queues, raw images, videos, model weights, and generated backups are
intentionally excluded from the repository. They are not required to run the local
demo and should be mounted separately when reproducing a training or HITL review.

Use the external asset bootstrap described in the project root `README.md` for the
runtime models and demo videos. For an evaluation replay, place the corresponding
queue/ground-truth files under this directory and keep generated outputs outside Git.

# Kubernetes manifests for Adversarial Video Protection

This folder contains raw Kubernetes manifests to deploy the stack into the `adv-protect` namespace.

Security note: do NOT store plaintext credentials in these manifests. They use environment-variable placeholders - set them at runtime (e.g., `kubectl create secret generic`) or with your deployment automation.

Quick deploy (minikube/kind):

```bash
kubectl apply -f k8s/namespace.yaml
kubectl -n adv-protect create secret generic app-secrets \
	--from-literal=DATABASE_URL="${DATABASE_URL}" \
	--from-literal=REDIS_URL="${REDIS_URL}"
kubectl apply -f k8s/
```

Customize: replace the example secret creation with your cloud secrets manager or Helm values. Do NOT store production credentials in plaintext in repo files or README examples.

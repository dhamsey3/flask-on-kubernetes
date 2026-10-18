# Flask on Kubernetes

A small Flask web app, a sample site for Dijato Geoservices, packaged as a non-root container and deployed to Kubernetes with health probes, resource limits and zero-downtime rolling updates. CI tests the app, builds and smoke-tests the image, and validates the manifests against the Kubernetes schemas.

## What's in it

**Container** ([`Dockerfile`](my_python_app/Dockerfile))
- Multi-stage build: compilers stay in the build stage, the runtime image has only the installed packages.
- Runs Gunicorn as a non-root user, with a Docker `HEALTHCHECK` on `/health`.

**Kubernetes** ([`namespace.yaml`](my_python_app/namespace.yaml), [`Deployment.yaml`](my_python_app/Deployment.yaml), [`Service.yaml`](my_python_app/Service.yaml))
- 3 replicas in their own namespace, rolling updates with `maxUnavailable: 0`.
- Pod hardening: non-root user, read-only root filesystem, all Linux capabilities dropped, no privilege escalation. `/tmp` is a writable `emptyDir`.
- Startup, liveness and readiness probes on `/health`; CPU and memory requests and limits.
- A `LoadBalancer` Service on port 80.

**App** ([`app.py`](my_python_app/app.py))

| Endpoint | Purpose |
|---|---|
| `/` | The site |
| `/health` | Probe target |
| `/api/services`, `/api/testimonials`, `/api/version` | JSON used by the page |
| `/contact` (POST) | Contact form: validated, length-capped, 5 requests per minute per client |
| `/metrics` | Prometheus request counter by endpoint and status |

Every response carries `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy` headers.

**CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)), on every push and pull request to `main`:
1. flake8 and the pytest suite.
2. Build the image, start it and check `/health`.
3. Validate the manifests with [kubeconform](https://github.com/yannh/kubeconform) in strict mode, so a misspelled field fails the build without needing a cluster.

## Run it on Minikube

Requirements: Docker, [Minikube](https://minikube.sigs.k8s.io/) and kubectl.

```sh
cd my_python_app
./deploy-local.sh                        # starts Minikube, builds the image inside it, applies the manifests
minikube service myapp-service -n dijato # opens the app
```

After a code change:

```sh
cd my_python_app
eval $(minikube docker-env)
docker build -t my-app:1.0.0 .
kubectl rollout restart deployment/myapp-deployment -n dijato
kubectl rollout status deployment/myapp-deployment -n dijato
```

Useful commands:

```sh
kubectl get pods -n dijato
kubectl logs -l app=my-app -n dijato --tail=40
kubectl port-forward svc/myapp-service 8080:80 -n dijato
```

## Run the tests

```sh
cd my_python_app
python -m pip install -r requirements.txt pytest
pytest
```

## Limitations

- Rate limits and metrics live in memory, so each Gunicorn worker in each pod keeps its own. With 3 pods and 2 workers each, a client can send more than 5 contact messages a minute, and `/metrics` shows one worker's counts. Shared limits need Redis; aggregated metrics need `prometheus_client`'s multiprocess mode.
- The contact form only logs messages; nothing is sent or stored.
- The services and testimonials are placeholder content.
- On Minikube, the `LoadBalancer` Service needs `minikube service` or `minikube tunnel` to be reachable.

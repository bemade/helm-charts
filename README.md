# Bemade Helm Charts

Welcome to our helm chart repository. This is where we store charts meant to be
installed on a Kubernetes cluster with helm. Typically, we install them from
the Rancher interface on our own cluster after synchronizing the repository.

## Repository Structure

Each helm chart is contained in a subfolder of this repository. In order to
function correctly, each helm chart folder must contain a `Chart.yaml` and a
`values.yaml` file at its root. It should also contain a variety of Kubernetes
resource templates in a `templates` subdirectory.

For more on helm charts, see the [Chart Template Developer's
Guide](https://helm.sh/docs/chart_template_guide/).

# Configure OpenShift CI access

The `rhdh-ci` nightly trigger uses a dedicated kubeconfig so setup does not disturb the user's
current cluster context.

1. Confirm `oc` is on `PATH`.
2. Create the dedicated configuration directory using the platform-native path equivalent of
   `~/.config/openshift-ci/`.
3. Let the human complete browser-mediated login:

   ```bash
   oc --kubeconfig ~/.config/openshift-ci/kubeconfig login --web \
     https://api.ci.l2s4.p1.openshiftapps.com:6443
   ```

4. Verify capability without printing a token:

   ```bash
   oc --kubeconfig ~/.config/openshift-ci/kubeconfig whoami
   oc --kubeconfig ~/.config/openshift-ci/kubeconfig whoami --show-server
   ```

5. Run the nightly trigger's `--dry-run` path. It returns a credential-free request for the private
   `gangway_adapter.py` boundary. That adapter alone retrieves the transient native `oc` credential
   and authenticates the request; the workflow never receives either value.

Report capability status only; do not include the user name, kubeconfig contents, bearer token, or
request headers. Any configuration change goes through the write gate.

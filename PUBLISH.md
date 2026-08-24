# Publish to GitHub + Tesserae catalog

Local git is ready (`main` @ v1.0.0 sources). GitHub CLI is installed; log in once, then create the public repo.

```sh
cd plugins/evcc_energy   # or wherever this checkout lives
gh auth login
gh repo create tesserae-evcc-energy --public --source=. --remote=origin --push --description "Tesserae widget for evcc: live house energy + PV forecast vs actual"
```

Tag the first release (catalog installs from the tarball URL):

```sh
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
curl -sL https://github.com/$(gh api user --jq .login)/tesserae-evcc-energy/archive/refs/tags/v1.0.0.tar.gz | shasum -a 256
```

Fill `catalog-entry.json` (`github`, `tarball_url`, `sha256`), take an `lg` screenshot from `/_test/render?plugin=evcc_energy&size=lg`, then open a PR on [dmellok/tesserae-widgets](https://github.com/dmellok/tesserae-widgets): add `screenshots/evcc_energy/lg.png` and append the entry to `widgets.json`.

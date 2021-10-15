# auth.itemize.no FusionAuth Theme
This repository contains the theme used for [auth.itemize.no](https://auth.itemize.no/). FusionAuth by itself does not allow version tracking. You can either edit the theme direction in the FusionAuth admin panel, but then you don't have any editor tools and can't revert changes. It is also hard to test themes before moving them into production.

## Testing
This repository contains a `template.py` script to automate the action of pushing and pulling the current theme. You can define API keys and FusionAuth API endpoint in  the `.env` file. A `template.env` has been added as a starting point. The API key will need GET and PUT permission to the `/api/theme` endpoint.

### Itemize Testing
We have a testing environment with it's own separate FusionAuth instance running at [auth.dev.itemize.no](https://auth.dev.itemize.no). Ask Drift for access. There you can easily push and pull themes without worrying to much of breaking stuff.
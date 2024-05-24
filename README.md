# Media Observer

A data / AI project to capture / analyse the evolution over time of the frontpages of main media sites.

A live version is available here (Please forgive the ugly UI 🥹 !) : http://18.171.236.162:8000/

_\* Hosted on an AWS free-tier EC2 instance + "12 months free" RDS database, managed with Terraform_

## What is this ?

This project aims at observing what subjects news medias put forward on their websites.

The basic process consists of :

* finding snapshots of those sites as they were at precise times of the day (e.g. at 8h, 12h, 18h and 22h),
* parse those snapshots to extract relevant info (e.g. the main headline),
* store that info in a local database,
* find semantic similarities within the headlines using language models

A basic web UI is available to display the results.

At the moment, 6 sites are supported (see them [there](src/media_observer/medias/__init__.py)) but the list will expand over time.

None of this would be possible without the incredible [Wayback Machine](http://web.archive.org/) and the volunteers that have helped setup the snapshotting of all those sites for decades.

## Installation

First you need to setup a PostgreSQL server and create a database whose path / credentials will be stored in a file `.secrets.toml` with the key `database_url`.

```
database_url="postgresql://user:password@yourdomain.com:port/database_name
```

### With Rye

1. Install Rye project manager (following instructions from https://rye.astral.sh/guide/installation/)
1. Install dependencies : `rye sync --no-lock --no-dev --all-features`

## Running the project

Setup your preferences by updating [the configuration file](./settings.toml)

### With Rye

* Do the site snapshots : `rye run snapshots`
* Compute the embeddings : `rye run embeddings`
* Build the similarity index : `rye run similarity_index`
* Run the web server : `rye run web_server`

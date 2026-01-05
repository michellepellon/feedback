# API Reference

This page documents the public API of the feedback package.

## Models

::: feedback.models.feed.Feed
    options:
      show_source: false

::: feedback.models.feed.Episode
    options:
      show_source: false

::: feedback.models.feed.QueueItem
    options:
      show_source: false

## Configuration

::: feedback.config.Config
    options:
      show_source: false

::: feedback.config.PlayerConfig
    options:
      show_source: false

::: feedback.config.KeyConfig
    options:
      show_source: false

::: feedback.config.load_config
    options:
      show_source: false

## Database

::: feedback.database.Database
    options:
      show_source: false
      members:
        - connect
        - close
        - get_feeds
        - upsert_feed
        - delete_feed
        - get_episodes
        - upsert_episode
        - update_progress

## Feed Fetcher

::: feedback.feeds.fetcher.FeedFetcher
    options:
      show_source: false
      members:
        - fetch
        - fetch_many

::: feedback.feeds.fetcher.FeedError
    options:
      show_source: false

::: feedback.feeds.fetcher.FeedFetchError
    options:
      show_source: false

::: feedback.feeds.fetcher.FeedParseError
    options:
      show_source: false

## Player

::: feedback.player.base.PlayerState
    options:
      show_source: false

::: feedback.player.base.BasePlayer
    options:
      show_source: false
      members:
        - state
        - position_ms
        - duration_ms
        - volume
        - rate
        - play
        - pause
        - resume
        - stop
        - seek
        - set_volume
        - set_rate

## Downloads

::: feedback.downloads.DownloadStatus
    options:
      show_source: false

::: feedback.downloads.DownloadItem
    options:
      show_source: false

::: feedback.downloads.DownloadQueue
    options:
      show_source: false
      members:
        - add
        - add_batch
        - cancel
        - cancel_all
        - clear_completed
        - get_items
        - set_progress_callback
        - wait_all

## Application

::: feedback.app.FeedbackApp
    options:
      show_source: false

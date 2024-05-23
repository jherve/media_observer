# de_quoi_parle_le_monde

### Bug

In the `featured_article_snapshot_id` view, the field `featured_article_snapshot_id` is taken as if it was unique by row, but it is not. 

This can be easily checked with this query :

```sql
SELECT * FROM (
    SELECT featured_article_snapshot_id, json_group_array(snapshot_id), COUNT(*) as count
    FROM snapshot_apparitions
    WHERE is_main -- Not required
    GROUP BY featured_article_snapshot_id
)
WHERE count > 1
```

Among other things it leads to "deadends" while browsing the UI, likely because the timestamp search and time diff relies on this false assumption.

2024-05-23 : This is likely not relevant anymore now that the URLs include the timestamp and not the snapshot_id.

### Different virtual timestamp, same timestamp

The snapshot process ends up choosing the same snapshot for different virtual timestamps.

This can be checked with this query :

```sql
SELECT
    sv.id, sv.site_id, sv2.id, sv2.site_id, sv.timestamp_virtual, sv2.timestamp_virtual, sv2.timestamp
FROM snapshots_view sv
CROSS JOIN snapshots_view sv2
WHERE
    sv.id != sv2.id
    and sv.timestamp = sv2.timestamp
```

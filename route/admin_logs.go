package route

import (
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/metatube-community/metatube-sdk-go/internal/logsearch"
	"github.com/metatube-community/metatube-sdk-go/internal/trace"
)

// parseLogQuery reads the shared log filter set from the query string. The same
// filters drive the Native and Graylog backends, so one filter bar controls both.
func parseLogQuery(c *gin.Context) logsearch.Query {
	query := logsearch.Query{
		TraceIDs:      c.QueryArray("trace_id"),
		RunID:         c.Query("run_id"),
		WindmillJobID: c.Query("windmill_job_id"),
		Text:          c.Query("q"),
		Component:     c.Query("component"),
		Level:         c.Query("level"),
		Provider:      c.Query("provider"),
	}
	if value := c.Query("limit"); value != "" {
		if parsed, err := strconv.Atoi(value); err == nil {
			query.Limit = parsed
		}
	}
	if value := c.Query("since"); value != "" {
		query.Since = parseTraceTime(value)
	}
	if value := c.Query("until"); value != "" {
		query.Until = parseTraceTime(value)
	}
	return query.Normalize()
}

// Actor log context is deliberately narrower than general Graylog search. The
// Default Stream contains unrelated homelab services, so the browser may only
// choose from these server-owned origins. The expected host is inventory
// context only where Docker records lack a server field; it is not proof of a
// particular line's host.
var actorLogOrigins = []struct {
	Key, Label, ExpectedHost string
	Origin                   logsearch.Origin
}{
	{"metatube1", "MetaTube 1 container", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube"}},
	{"metatube1", "MetaTube 1 application", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube-server", Server: "kraken"}},
	{"metatube2", "MetaTube 2", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube2"}},
	{"bridge1", "Provider bridge 1", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube-provider-bridge"}},
	{"bridge2", "Provider bridge 2", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube2-provider-bridge"}},
	{"resolver", "Actor resolver", "kraken", logsearch.Origin{Application: "jav_actor_db", Environment: "homelab", Service: "jav-actor-resolver"}},
	{"watcher", "Actor identify watcher", "kraken", logsearch.Origin{Application: "jav_actor_db", Environment: "homelab", Service: "jav-actor-identify-watcher"}},
	{"browser", "Actor browser", "kraken", logsearch.Origin{Application: "jav_actor_db", Environment: "homelab", Service: "jav-actor-browser"}},
	{"windmill", "Windmill", "unraid", logsearch.Origin{Application: "windmill", Environment: "homelab", Service: "windmill-1"}},
	{"emby", "Emby", "kraken", logsearch.Origin{Application: "emby", Environment: "homelab", Service: "EmbyServer"}},
	{"actor-db", "Actor database", "kraken", logsearch.Origin{Application: "jav_actor_db", Environment: "homelab", Service: "jav-actor-db-postgres"}},
	{"flaresolverr", "FlareSolverr", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube-flaresolverr"}},
	{"flaresolverr2", "FlareSolverr 2", "kraken", logsearch.Origin{Application: "metatube", Environment: "homelab", Service: "metatube2-flaresolverr"}},
}

func getActorStackLogs(searcher *logsearch.Searcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		now := time.Now().UTC()
		until := now
		if value := parseTraceTime(c.Query("until")); value != nil && value.Before(now) {
			until = *value
		}
		since := until.Add(-5 * time.Minute)
		if value := parseTraceTime(c.Query("since")); value != nil {
			since = *value
		}
		if since.After(until) {
			since = until.Add(-5 * time.Minute)
		}
		if since.Before(until.Add(-30 * time.Minute)) {
			since = until.Add(-30 * time.Minute)
		}
		query := logsearch.Query{Text: c.Query("q"), Since: &since, Until: &until, Limit: 200}
		if len([]rune(query.Text)) > 100 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Search text is too long"})
			return
		}
		if value := c.Query("limit"); value != "" {
			if parsed, err := strconv.Atoi(value); err == nil {
				query.Limit = parsed
			}
		}
		selected := c.Query("service")
		scope := make([]gin.H, 0, len(actorLogOrigins))
		for _, item := range actorLogOrigins {
			if selected == "" || selected == item.Key {
				scope = append(scope, gin.H{"key": item.Key, "label": item.Label, "expected_host": item.ExpectedHost, "application": item.Origin.Application, "environment": item.Origin.Environment, "server": item.Origin.Server, "service": item.Origin.Service})
				query.Origins = append(query.Origins, item.Origin)
			}
		}
		if len(query.Origins) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unknown actor service"})
			return
		}
		result := searcher.Search(c.Request.Context(), query, []logsearch.Source{logsearch.SourceGraylog})[0]
		c.JSON(http.StatusOK, gin.H{"result": result, "scope": scope, "correlated": false, "effective": result.Effective})
	}
}

// parseLogSources reads the requested sources, defaulting to every source.
func parseLogSources(c *gin.Context) []logsearch.Source {
	values := c.QueryArray("source")
	sources := make([]logsearch.Source, 0, len(values))
	for _, value := range values {
		if logsearch.ValidSource(value) {
			sources = append(sources, logsearch.Source(strings.ToLower(strings.TrimSpace(value))))
		}
	}
	return sources
}

// getAdminLogs serves the recent native log buffer. The legacy `entries` field is
// kept for the general LOGS tab, and the same request now applies server-side
// filters so the UI never has to download every line to filter it.
func getAdminLogs(searcher *logsearch.Searcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		query := parseLogQuery(c)
		result := searcher.Search(c.Request.Context(), query, []logsearch.Source{logsearch.SourceNative})[0]

		entries := make([]gin.H, 0, len(result.Lines))
		for _, line := range result.Lines {
			entries = append(entries, gin.H{
				"at":          line.At,
				"message":     line.Message,
				"source":      line.Source,
				"badge":       line.Badge,
				"level":       line.Level,
				"component":   line.Component,
				"provider":    line.Provider,
				"trace_id":    line.TraceID,
				"fingerprint": line.Fingerprint,
			})
		}
		c.JSON(http.StatusOK, gin.H{
			"entries":     entries,
			"truncated":   result.Truncated,
			"match_count": result.MatchCount,
			"retention":   result.Retention,
			"effective":   result.Effective,
		})
	}
}

// getAdminLogSearch returns every requested source side by side, each with its own
// status, so a slow or broken Graylog can never delay or fail the trace timeline.
func getAdminLogSearch(searcher *logsearch.Searcher) gin.HandlerFunc {
	return func(c *gin.Context) {
		query := parseLogQuery(c)
		sources := parseLogSources(c)
		results := searcher.Search(c.Request.Context(), query, sources)

		lines := make([]logsearch.Line, 0, 64)
		for _, result := range results {
			lines = append(lines, result.Lines...)
		}
		deduped, hidden := logsearch.Deduplicate(lines)

		cfg := searcher.GraylogConfig()
		c.JSON(http.StatusOK, gin.H{
			"results":      results,
			"deduplicated": deduped,
			"hidden":       hidden,
			"effective":    query,
			"graylog": gin.H{
				"configured":        cfg.Configured(),
				"enabled":           cfg.Enabled,
				"missing_token":     cfg.EnabledWithoutToken(),
				"external_url":      cfg.ExternalURL,
				"max_results":       cfg.MaxResults,
				"max_range_hours":   cfg.MaxRangeHours,
				"timeout_seconds":   int(cfg.Timeout.Seconds()),
				"search_api":        "search/universal/absolute",
				"credential_source": cfg.TokenSourceLabel(),
				"credential_error":  cfg.TokenFileErr,
			},
			"retention": gin.H{
				"native":  logsearch.NativeRetention,
				"graylog": "Durable; retention is managed by Graylog",
				"trace":   "Structured trace events follow the configured trace retention",
			},
		})
	}
}

// getTraceRun returns one grouped run: its explicitly related traces and their
// ordered events in a single bounded response.
func getTraceRun(service *trace.Service) gin.HandlerFunc {
	return func(c *gin.Context) {
		eventLimit, _ := strconv.Atoi(c.DefaultQuery("events", strconv.Itoa(trace.MaxRunEvents)))
		group, err := service.ResolveRun(c.Param("runID"), eventLimit)
		if err != nil {
			abortWithTraceError(c, err)
			return
		}
		downstream := make([]gin.H, 0, len(group.Traces))
		for _, run := range group.Traces {
			downstream = append(downstream, gin.H{
				"trace_id":         run.TraceID,
				"downstream":       trace.DownstreamFor(run),
				"awaiting_report":  trace.DownstreamFor(run).Awaiting,
				"events_available": run.EventCount,
			})
		}
		c.JSON(http.StatusOK, gin.H{
			"run":             group,
			"downstream":      downstream,
			"bounds":          gin.H{"max_traces": trace.MaxRunTraces, "max_events": trace.MaxRunEvents},
			"awaiting_report": awaitingAny(group.Traces),
		})
	}
}

func awaitingAny(runs []trace.Run) bool {
	for _, run := range runs {
		if trace.DownstreamFor(run).Awaiting {
			return true
		}
	}
	return false
}

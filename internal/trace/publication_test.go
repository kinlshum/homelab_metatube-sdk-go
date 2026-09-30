package trace

import (
	"github.com/stretchr/testify/require"
	"testing"
)

func TestPublicationRequiresAppliedReceiptNotTwoReporters(t *testing.T) {
	s := newTestService(t, nil)
	h, ok := s.Start(StartInput{Kind: KindActor, Operation: OperationPublish, RunID: "actor-save-1"})
	require.True(t, ok)
	h.Event(Event{Component: ComponentWindmill, Stage: StageWindmillStarted})
	h.Event(Event{Component: ComponentEmby, Stage: StageEmbyWrite})
	run, err := s.Finish(h.TraceID(), FinishInput{Status: StatusRunning, PublicationStatus: "reload_pending", PublicationOrigin: "actor_editor"})
	require.NoError(t, err)
	require.True(t, DownstreamFor(*run).Awaiting)
	require.NotEqual(t, DownstreamComplete, DownstreamFor(*run).Status)
	run, err = s.Finish(h.TraceID(), FinishInput{Status: StatusSucceeded, PublicationStatus: "applied"})
	require.NoError(t, err)
	require.Equal(t, DownstreamComplete, DownstreamFor(*run).Status)
	require.Equal(t, "actor_editor", run.PublicationOrigin)
	require.NotNil(t, run.CompletedAt)
}

func TestLookupCannotAcquirePublicationBadge(t *testing.T) {
	s := newTestService(t, nil)
	h, _ := s.Start(StartInput{Kind: KindActor, Operation: OperationLookup})
	run, err := s.Finish(h.TraceID(), FinishInput{Status: StatusSucceeded, PublicationStatus: "applied"})
	require.NoError(t, err)
	require.Empty(t, run.PublicationStatus)
	require.Equal(t, DownstreamUnavailable, DownstreamFor(*run).Status)
}

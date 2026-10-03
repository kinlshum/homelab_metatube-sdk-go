//go:build experimental

package engine

import (
	"strings"
	"testing"

	mt "github.com/metatube-community/metatube-sdk-go/provider"
)

func TestExperimentalReleaseProviderRegistration(t *testing.T) {
	movies, actors := map[string]bool{}, map[string]bool{}
	for name := range mt.RangeMovieFactory {
		movies[strings.ToLower(name)] = true
	}
	for name := range mt.RangeActorFactory {
		actors[strings.ToLower(name)] = true
	}
	if !movies["avbase"] {
		t.Fatal("release must register AVBASE movie provider")
	}
	if !actors["av-league"] {
		t.Fatal("release must register AV-LEAGUE actor provider")
	}
}

package promptdata

import "embed"

//go:embed *.md
var files embed.FS

func mustRead(name string) string {
	b, err := files.ReadFile(name)
	if err != nil {
		panic("promptdata: read " + name + ": " + err.Error())
	}
	return string(b)
}

// OptimizerSystemPrompt is the full system prompt for the prompt optimizer (brief).
func OptimizerSystemPrompt() string {
	return MustJoinRules(OptimizerBundle)
}

// SlideGeneratorSystemPrompt is the full system prompt for carousel slide HTML generation.
func SlideGeneratorSystemPrompt() string {
	return MustJoinRules(SlideGeneratorBundle)
}

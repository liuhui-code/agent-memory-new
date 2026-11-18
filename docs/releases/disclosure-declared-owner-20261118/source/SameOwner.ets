class Both { render() { SymbolGlyph('arrow').rotate({angle:this.opened?0:180}); } toggle() { this.opened=!this.opened; } }

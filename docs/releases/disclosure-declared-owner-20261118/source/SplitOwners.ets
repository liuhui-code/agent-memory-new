class Read { render() { SymbolGlyph('arrow').rotate({angle:this.opened?0:180}); } }
class Write { toggle() { this.opened=!this.opened; } }

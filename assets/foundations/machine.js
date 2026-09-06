// Generic interpreter of tables compiled from scripts/audit_device.py:models.
// It contains no per-device transitions and reads no state from glTF.
export function machine(table) {
  let current = table.initial;
  return {
    get index() { return current; },
    get state() { return table.states[current]; },
    get moves() { return table.moves[current].slice(); },
    move(next) {
      if (!Number.isInteger(next) || !table.moves[current].includes(next)) {
        throw new Error('Move is outside the audited transition table');
      }
      current = next;
      return table.states[current];
    }
  };
}

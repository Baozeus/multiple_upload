"""Reserved HTTP transport boundary.

The current application uses the TCP adapter. Keeping this module explicit
lets a future HTTP implementation conform to the same client-side contract
without leaking protocol details into the UI.
"""

# Small Team

Flipcommons is a volunteer-run, not-for-profit project. Our mission is to further pinball knowledge, not make money.

To survive, the system must stay **lean**:

- **Low maintenance**. Nobody's manning this on a day-to-day basis so ongoing maintenance must be MINIMAL. For example, rotating HTTP certs manually is a no-no. Automatic security patches to our packages is mandatory.
- **Runnable by part-time developers without DevOps training.** For services like CDN, file sharing, auth, choose systems that are NOT aimed at professional IT.
- **Easy to operate.** Minimal moving parts.
- **Easy to onboard.** A new contributor should be productive on day one.
- **No single person failure**. Volunteers, even founders, disappear. Ensure no one person has the keys to the kingdom.

Every architectural and operational decision must be weighed against these constraints. Prefer boring, hosted, well-documented choices over clever ones. When in doubt, choose the option a part-time volunteer can keep running a year from now.

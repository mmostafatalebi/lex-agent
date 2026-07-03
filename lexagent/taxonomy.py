"""Canonical and risky clause examples across the nine substantive clause types.

Each type carries two canonical examples (``is_risky=False``) and one recognizably
problematic example (``is_risky=True``). These seed the retrieval taxonomy so
clause analysis can compare candidate language against known-good and known-bad
patterns.
"""

from pydantic import BaseModel

from lexagent.models import ClauseType


class TaxonomyEntry(BaseModel):
    clause_type: ClauseType
    text: str
    is_risky: bool
    notes: str


TAXONOMY: list[TaxonomyEntry] = [
    TaxonomyEntry(
        clause_type=ClauseType.IP_ASSIGNMENT,
        text=(
            "Contractor assigns to Client all right, title, and interest in the deliverables "
            "created specifically for Client under the applicable statement of work. Contractor "
            "retains ownership of any pre-existing materials, tools, and know-how, and grants "
            "Client a perpetual, non-exclusive license to use those materials solely as "
            "embedded in the deliverables."
        ),
        is_risky=False,
        notes=(
            "Assignment is scoped to work created for the engagement and preserves the "
            "contractor's background IP, which is the balanced market standard."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.IP_ASSIGNMENT,
        text=(
            "Upon full payment of all fees due, Contractor assigns to Client the copyright in "
            "the final deliverables accepted by Client. Contractor may retain and reuse general "
            "skills, methods, and non-client-specific components developed in the course of the "
            "work, provided no Client confidential information is disclosed."
        ),
        is_risky=False,
        notes=(
            "Ties the assignment to payment and lets the contractor keep reusable, generic "
            "components, a fair allocation for professional services."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.IP_ASSIGNMENT,
        text=(
            "Contractor hereby irrevocably assigns to Client all intellectual property of every "
            "kind, including all works conceived before the Effective Date and all works "
            "developed during the term whether or not related to the services. Contractor "
            "waives all moral rights and agrees that Client owns any invention Contractor "
            "creates during the term."
        ),
        is_risky=True,
        notes=(
            "Sweeps in the contractor's pre-existing and unrelated IP, a classic overreaching "
            "grab that strips the contractor of assets never meant to be sold."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.PAYMENT_TERMS,
        text=(
            "Client shall pay each undisputed invoice within thirty (30) days of receipt. "
            "Amounts not paid when due accrue interest at 1.5% per month or the maximum rate "
            "permitted by law, whichever is lower. Client may withhold only those amounts it "
            "disputes in good faith, and shall pay all undisputed amounts on time."
        ),
        is_risky=False,
        notes=(
            "Defines a clear net-30 timeline, a late fee, and limits withholding to good-faith "
            "disputes, protecting the contractor's cash flow."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.PAYMENT_TERMS,
        text=(
            "Fees are payable in milestones as set out in the statement of work, with a 30% "
            "deposit due on signing and the balance due on acceptance of each milestone. Client "
            "shall notify Contractor of any milestone deficiency within ten (10) business days, "
            "failing which the milestone is deemed accepted and payable."
        ),
        is_risky=False,
        notes=(
            "Milestone billing with a deposit and a deemed-acceptance window gives both sides "
            "predictable, enforceable payment triggers."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.PAYMENT_TERMS,
        text=(
            "Client shall pay Contractor following receipt and review of each invoice. Client "
            "reserves the right to withhold payment for any reason it deems appropriate, and no "
            "payment is due to Contractor until Client has itself been paid by its end customer "
            "for the related work."
        ),
        is_risky=True,
        notes=(
            "Provides no payment deadline, allows discretionary withholding, and adds a "
            "pay-when-paid condition that shifts the customer's credit risk onto the "
            "contractor."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.TERMINATION,
        text=(
            "Either party may terminate this Agreement for convenience on thirty (30) days' "
            "written notice. Upon termination, Client shall pay Contractor for all services "
            "performed and expenses incurred through the effective date of termination, "
            "including work in progress on a pro-rata basis."
        ),
        is_risky=False,
        notes=(
            "Symmetric convenience termination with payment for work performed treats both "
            "parties equally and protects earned fees."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.TERMINATION,
        text=(
            "Either party may terminate for material breach if the breaching party fails to "
            "cure within fifteen (15) days after written notice describing the breach. "
            "Termination does not relieve Client of its obligation to pay for services accepted "
            "before the effective date of termination."
        ),
        is_risky=False,
        notes=(
            "Termination for cause with a cure period and preserved payment rights is standard "
            "and even-handed."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.TERMINATION,
        text=(
            "Client may terminate this Agreement at any time, for any reason or no reason, "
            "effective immediately upon notice. Contractor may not terminate prior to "
            "completion of all outstanding work. Client has no obligation to pay for any work "
            "in progress that has not been accepted as of the date of termination."
        ),
        is_risky=True,
        notes=(
            "One-sided at-will termination that binds only the contractor and denies pay for "
            "unaccepted work in progress leaves the contractor exposed."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.LIABILITY,
        text=(
            "Except for breaches of confidentiality or infringement of intellectual property, "
            "each party's total liability under this Agreement shall not exceed the fees paid "
            "or payable in the twelve (12) months preceding the claim. Neither party is liable "
            "for indirect, incidental, or consequential damages."
        ),
        is_risky=False,
        notes=(
            "A mutual cap tied to fees with carve-outs for confidentiality and IP is the widely "
            "accepted allocation of risk for services work."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.LIABILITY,
        text=(
            "Each party's aggregate liability arising out of this Agreement is limited to the "
            "total fees paid under the applicable statement of work, and neither party shall be "
            "liable for lost profits or loss of data. This limitation does not apply to a "
            "party's indemnification obligations or gross negligence."
        ),
        is_risky=False,
        notes=(
            "Caps liability at contract value while carving out indemnity and gross negligence, "
            "a reasonable and mutual limitation."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.LIABILITY,
        text=(
            "Contractor shall be liable for any and all damages, losses, costs, and expenses of "
            "any kind arising out of or relating to this Agreement, without limitation as to "
            "amount and regardless of the theory of liability. Contractor's liability is not "
            "limited to the fees paid under the applicable statement of work."
        ),
        is_risky=True,
        notes=(
            "Uncapped, one-directional liability with no exclusion of consequential damages "
            "exposes the contractor to losses far exceeding the contract value."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.CONFIDENTIALITY,
        text=(
            "Each party shall protect the other's confidential information with at least "
            "reasonable care and use it solely to perform this Agreement. These obligations "
            "survive for three (3) years after termination and do not apply to information that "
            "is public, already known, independently developed, or rightfully received from a "
            "third party."
        ),
        is_risky=False,
        notes=(
            "Mutual duty with the customary exclusions and a defined survival period reflects "
            "standard, enforceable confidentiality terms."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.CONFIDENTIALITY,
        text=(
            "Confidential Information means non-public information disclosed in writing and "
            "marked confidential, or disclosed orally and confirmed in writing within thirty "
            "days. On termination, the receiving party shall return or destroy the disclosing "
            "party's confidential information at the disclosing party's request."
        ),
        is_risky=False,
        notes=(
            "A bounded definition plus a return-or-destroy obligation keeps confidentiality "
            "scoped and administrable for both sides."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.CONFIDENTIALITY,
        text=(
            "All information of any kind that Contractor learns or observes in connection with "
            "Client is Client's confidential information in perpetuity, whether or not marked. "
            "Contractor is prohibited from using any residual knowledge, including general "
            "skills and experience, for any other client at any time."
        ),
        is_risky=True,
        notes=(
            "A perpetual, unmarked, one-sided definition that bars use of residual skills "
            "effectively prevents the contractor from working elsewhere."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.INDEMNIFICATION,
        text=(
            "Each party shall indemnify the other against third-party claims arising from its "
            "own breach of this Agreement or its negligence. The indemnified party shall "
            "promptly notify the indemnifying party, allow it to control the defense, and "
            "provide reasonable cooperation at the indemnifying party's expense."
        ),
        is_risky=False,
        notes=(
            "Mutual, fault-based indemnity with standard notice-and-control mechanics fairly "
            "assigns responsibility to the party at fault."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.INDEMNIFICATION,
        text=(
            "Contractor shall indemnify Client against third-party claims that the deliverables "
            "infringe a patent, copyright, or trade secret, provided Client gives prompt notice "
            "and cooperation. Contractor's indemnity obligation is subject to the limitation of "
            "liability in this Agreement."
        ),
        is_risky=False,
        notes=(
            "A scoped IP-infringement indemnity that remains subject to the liability cap is a "
            "common and reasonable contractor commitment."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.INDEMNIFICATION,
        text=(
            "Contractor shall defend, indemnify, and hold harmless Client from any and all "
            "claims of any nature whatsoever, including claims arising from Client's own "
            "negligence, with no limitation of liability. Contractor shall pay all defense "
            "costs and attorneys' fees regardless of the outcome of the claim."
        ),
        is_risky=True,
        notes=(
            "Uncapped indemnity that covers the client's own negligence and every category of "
            "claim forces the contractor to insure risks it does not control."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.NON_COMPETE,
        text=(
            "During the term and for twelve (12) months afterward, Contractor shall not solicit "
            "for employment any employee of Client with whom Contractor worked directly, nor "
            "solicit the specific Client accounts Contractor served, using Client confidential "
            "information. This restriction does not limit Contractor from serving other clients "
            "generally."
        ),
        is_risky=False,
        notes=(
            "A narrow, twelve-month non-solicit tied to actual accounts and confidential "
            "information protects legitimate interests without blocking the contractor's "
            "livelihood."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.NON_COMPETE,
        text=(
            "For six (6) months after termination, Contractor shall not provide services that "
            "are directly competitive with the specific product Contractor worked on, within "
            "the geographic markets where Client actively sells that product. Contractor "
            "remains free to work in all other fields and locations."
        ),
        is_risky=False,
        notes=(
            "A short, narrowly tailored restriction limited to the specific product and market "
            "is the kind of non-compete courts routinely enforce."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.NON_COMPETE,
        text=(
            "During the term and for three (3) years after termination, Contractor shall not, "
            "directly or indirectly, engage in or provide services to any business anywhere in "
            "the world that offers software, consulting, or technology services of any kind. "
            "Contractor agrees this restriction is reasonable and necessary."
        ),
        is_risky=True,
        notes=(
            "A three-year, worldwide, whole-industry ban is grossly overbroad, likely "
            "unenforceable, and would prevent the contractor from working at all."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.DISPUTE_RESOLUTION,
        text=(
            "The parties shall first attempt to resolve any dispute through good-faith "
            "negotiation. If unresolved within thirty (30) days, the dispute shall be settled "
            "by binding arbitration under the AAA Commercial Rules before a single arbitrator, "
            "seated in a location mutually agreed by the parties, with each party bearing its "
            "own costs."
        ),
        is_risky=False,
        notes=(
            "Escalation to negotiation before a neutral, mutually located arbitration keeps "
            "dispute resolution balanced and predictable."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.DISPUTE_RESOLUTION,
        text=(
            "Any dispute shall be governed by the laws of the State of Delaware and resolved in "
            "the state or federal courts located there. The parties first agree to non-binding "
            "mediation, and the prevailing party in any subsequent litigation is entitled to "
            "recover its reasonable attorneys' fees."
        ),
        is_risky=False,
        notes=(
            "A clear governing-law and venue clause with a mediation step and a "
            "prevailing-party fee provision is standard and reciprocal."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.DISPUTE_RESOLUTION,
        text=(
            "All disputes shall be resolved exclusively by binding arbitration seated in "
            "Client's home jurisdiction, applying that jurisdiction's law. Contractor waives "
            "any right to a jury trial and to participate in any class or collective action, "
            "and shall bear all costs and fees of the arbitration regardless of outcome."
        ),
        is_risky=True,
        notes=(
            "Forcing arbitration in the client's home forum while making the contractor pay all "
            "costs and waive class rights creates a lopsided, deterrent process."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.SCOPE_OF_WORK,
        text=(
            "Contractor shall perform the services described in each statement of work, which "
            "defines the deliverables, milestones, and acceptance criteria. Any change to the "
            "scope, schedule, or fees must be agreed in a written change order signed by both "
            "parties before the additional work begins."
        ),
        is_risky=False,
        notes=(
            "Anchoring scope to a written SOW and requiring signed change orders prevents scope "
            "creep and keeps additional work compensated."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.SCOPE_OF_WORK,
        text=(
            "Deliverables are subject to acceptance testing against the criteria in the "
            "statement of work. Contractor shall provide up to two rounds of revisions to "
            "correct deficiencies identified in writing; revisions beyond that scope are billed "
            "at Contractor's standard hourly rate."
        ),
        is_risky=False,
        notes=(
            "Bounded acceptance testing and a defined number of revision rounds set clear "
            "expectations and protect the contractor from open-ended rework."
        ),
    ),
    TaxonomyEntry(
        clause_type=ClauseType.SCOPE_OF_WORK,
        text=(
            "Contractor shall perform whatever services Client reasonably requests from time to "
            "time related to the project, at no additional charge beyond the fixed fee. Client "
            "may request unlimited revisions until fully satisfied, and Contractor shall "
            "continue working until Client confirms acceptance in its sole discretion."
        ),
        is_risky=True,
        notes=(
            "Open-ended scope with unlimited free revisions and sole-discretion acceptance "
            "invites unbounded, uncompensated work."
        ),
    ),
]

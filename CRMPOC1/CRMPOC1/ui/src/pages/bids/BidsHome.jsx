import BidList from "./BidList.jsx";
import VendorBids from "./VendorBids.jsx";
import { useBidSide } from "./bidUi.jsx";

/** /bids shows the bid team's list, or a vendor's own bids. */
export default function BidsHome() {
  const side = useBidSide();
  return side.manager ? <BidList /> : <VendorBids />;
}

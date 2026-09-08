import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import Layout from "./layout/Layout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import VendorDashboard from "./pages/VendorDashboard.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import ComplaintList from "./pages/complaints/ComplaintList.jsx";
import ComplaintCreate from "./pages/complaints/ComplaintCreate.jsx";
import ComplaintDetail from "./pages/complaints/ComplaintDetail.jsx";
import InstallationList from "./pages/installations/InstallationList.jsx";
import InstallationCreate from "./pages/installations/InstallationCreate.jsx";
import InstallationDetail from "./pages/installations/InstallationDetail.jsx";
import CallList from "./pages/calls/CallList.jsx";
import CallCreate from "./pages/calls/CallCreate.jsx";
import CallDetail from "./pages/calls/CallDetail.jsx";
import PendingFollowUps from "./pages/calls/PendingFollowUps.jsx";
import Calendar from "./pages/calls/Calendar.jsx";
import UserList from "./pages/admin/UserList.jsx";
import RoleList from "./pages/admin/RoleList.jsx";
import Permissions from "./pages/admin/Permissions.jsx";
import PaymentHistory from "./pages/admin/PaymentHistory.jsx";
import ProjectList from "./pages/projects/ProjectList.jsx";
import ProjectDetail from "./pages/projects/ProjectDetail.jsx";
import ItemMasterList from "./pages/item_masters/ItemMasterList.jsx";
import ItemMasterCreate from "./pages/item_masters/ItemMasterCreate.jsx";
import ItemMasterDetail from "./pages/item_masters/ItemMasterDetail.jsx";
import CourierList from "./pages/couriers/CourierList.jsx";
import CourierCreate from "./pages/couriers/CourierCreate.jsx";
import CourierDetail from "./pages/couriers/CourierDetail.jsx";
import MarketDashboard from "./pages/market/MarketDashboard.jsx";
import MarketUsers from "./pages/market/MarketUsers.jsx";
import MarketItems from "./pages/market/MarketItems.jsx";
import MarketOrders from "./pages/market/MarketOrders.jsx";
import MarketCategories from "./pages/market/MarketCategories.jsx";
import ClaimList from "./pages/claims/ClaimList.jsx";
import ClaimCreate from "./pages/claims/ClaimCreate.jsx";
import ClaimDetail from "./pages/claims/ClaimDetail.jsx";
import OrderList from "./pages/orders/OrderList.jsx";
import OrderCreate from "./pages/orders/OrderCreate.jsx";
import OrderDetail from "./pages/orders/OrderDetail.jsx";
import SerialDetails from "./pages/SerialDetails.jsx";
import SerialHistory from "./pages/serials/SerialHistory.jsx";
import ServiceRequestList from "./pages/services/ServiceRequestList.jsx";
import ServiceRequestCreate from "./pages/services/ServiceRequestCreate.jsx";
import ServiceRequestDetail from "./pages/services/ServiceRequestDetail.jsx";
import EngineerAssignedUnits from "./pages/services/EngineerAssignedUnits.jsx";
import ServiceDocumentUploadPublic from "./pages/services/ServiceDocumentUploadPublic.jsx";
import PartnerRegistrationList from "./pages/partners/PartnerRegistrationList.jsx";
import PartnerRegistrationReview from "./pages/partners/PartnerRegistrationReview.jsx";
import PartnerRegistrationPublic from "./pages/partners/PartnerRegistrationPublic.jsx";
import PartnerAgreementSign from "./pages/partners/PartnerAgreementSign.jsx";
import { isOperationsAdminRole, isPartnerAdminRole, isSystemAdminRole } from "./utils/roles.js";

function OperationsAdminRoute({ children }) {
  const { user } = useAuth();
  if (!isOperationsAdminRole(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function PartnerAdminRoute({ children }) {
  const { user } = useAuth();
  if (!isPartnerAdminRole(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function SystemAdminRoute({ children }) {
  const { user } = useAuth();
  if (!isSystemAdminRole(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function DefaultLanding() {
  const { user } = useAuth();
  if (user?.role === "vendor") {
    return <Navigate to="/vendor-dashboard" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}

function DashboardRoute() {
  const { user } = useAuth();
  if (user?.role === "vendor") {
    return <VendorDashboard />;
  }
  return <Dashboard />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/partner-registration/:token" element={<PartnerRegistrationPublic />} />
      <Route path="/partner-agreement/:token" element={<PartnerAgreementSign />} />
      <Route path="/services/public-upload/:token" element={<ServiceDocumentUploadPublic />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DefaultLanding />} />
        <Route path="/dashboard" element={<DashboardRoute />} />
        <Route path="/vendor-dashboard" element={<VendorDashboard />} />
        <Route path="/calls" element={<CallList />} />
        <Route path="/calls/new" element={<CallCreate />} />
        <Route path="/calls/pending-follow-ups" element={<PendingFollowUps />} />
        <Route path="/calls/calendar" element={<Calendar />} />
        <Route path="/calls/:id" element={<CallDetail />} />
        <Route path="/admin/users" element={<SystemAdminRoute><UserList /></SystemAdminRoute>} />
        <Route path="/admin/roles" element={<SystemAdminRoute><RoleList /></SystemAdminRoute>} />
        <Route path="/admin/permissions" element={<SystemAdminRoute><Permissions /></SystemAdminRoute>} />
        <Route path="/admin/payments" element={<SystemAdminRoute><PaymentHistory /></SystemAdminRoute>} />
        <Route path="/admin/partner-registrations" element={<PartnerAdminRoute><PartnerRegistrationList /></PartnerAdminRoute>} />
        <Route path="/admin/partner-registrations/:id/review" element={<PartnerAdminRoute><PartnerRegistrationReview /></PartnerAdminRoute>} />
        <Route path="/complaints" element={<ComplaintList />} />
        <Route path="/complaints/new" element={<ComplaintCreate />} />
        <Route path="/complaints/:id" element={<ComplaintDetail />} />
        <Route path="/services" element={<ServiceRequestList />} />
        <Route path="/services/my-units" element={<EngineerAssignedUnits />} />
        <Route path="/services/new" element={<ServiceRequestCreate />} />
        <Route path="/services/:id" element={<ServiceRequestDetail />} />
        <Route path="/items" element={<ItemMasterList />} />
        <Route path="/items/new" element={<ItemMasterCreate />} />
        <Route path="/items/:id" element={<ItemMasterDetail />} />
        <Route path="/couriers" element={<OperationsAdminRoute><CourierList /></OperationsAdminRoute>} />
        <Route path="/couriers/new" element={<OperationsAdminRoute><CourierCreate /></OperationsAdminRoute>} />
        <Route path="/couriers/:id" element={<OperationsAdminRoute><CourierDetail /></OperationsAdminRoute>} />
        <Route path="/orders" element={<OrderList />} />
        <Route path="/orders/new" element={<OrderCreate />} />
        <Route path="/orders/:id" element={<OrderDetail />} />
        <Route path="/installations" element={<InstallationList />} />
        <Route path="/installations/new" element={<InstallationCreate />} />
        <Route path="/installations/:id" element={<InstallationDetail />} />
        <Route path="/claims" element={<ClaimList />} />
        <Route path="/claims/new" element={<ClaimCreate />} />
        <Route path="/claims/:id" element={<ClaimDetail />} />
        <Route path="/market-admin/dashboard" element={<MarketDashboard />} />
        <Route path="/market-admin/users" element={<MarketUsers />} />
        <Route path="/market-admin/items" element={<MarketItems />} />
        <Route path="/market-admin/orders" element={<MarketOrders />} />
        <Route path="/market-admin/categories" element={<MarketCategories />} />
        <Route path="/market-admin/vendors" element={<Placeholder title="Vendor Registrations" />} />
        <Route path="/market-admin/media" element={<Placeholder title="Media Manager" />} />
        <Route path="/projects" element={<ProjectList />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/serials/details" element={<SerialDetails />} />
        <Route path="/serials/history" element={<OperationsAdminRoute><SerialHistory /></OperationsAdminRoute>} />
      </Route>
      <Route path="*" element={<DefaultLanding />} />
    </Routes>
  );
}

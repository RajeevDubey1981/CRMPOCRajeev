-- MySQL dump 10.13  Distrib 8.0.46, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: indcool
-- ------------------------------------------------------
-- Server version	8.0.46-0ubuntu0.24.04.3

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('0037_partner_agreements');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `calls`
--

DROP TABLE IF EXISTS `calls`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `calls` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ref_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `call_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `priority` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_to` int DEFAULT NULL,
  `transferred_to` int DEFAULT NULL,
  `is_transferred` tinyint(1) NOT NULL DEFAULT '0',
  `duration_secs` int DEFAULT NULL,
  `call_datetime` datetime DEFAULT NULL,
  `followup_date` datetime DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `follow_up_notes` text COLLATE utf8mb4_unicode_ci,
  `follow_up_status` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `complaint_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_calls_ref_no` (`ref_no`),
  KEY `assigned_to` (`assigned_to`),
  KEY `transferred_to` (`transferred_to`),
  KEY `complaint_id` (`complaint_id`),
  CONSTRAINT `calls_ibfk_1` FOREIGN KEY (`assigned_to`) REFERENCES `users` (`id`),
  CONSTRAINT `calls_ibfk_2` FOREIGN KEY (`transferred_to`) REFERENCES `users` (`id`),
  CONSTRAINT `calls_ibfk_3` FOREIGN KEY (`complaint_id`) REFERENCES `complaints` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `calls`
--

LOCK TABLES `calls` WRITE;
/*!40000 ALTER TABLE `calls` DISABLE KEYS */;
INSERT INTO `calls` VALUES (1,'CALL-2026-0001','Vendor1 Customer','customer1@test.com','9876543210','Inbound','Closed','high',5,NULL,0,420,'2026-08-07 09:15:00','2026-08-08 10:00:00','Customer reported cooler issue','Issue tracked under complaint','Done',1,'2026-08-23 03:55:40','2026-08-23 03:55:40'),(2,'CALL-2026-0002','Test Customer Two','customer2@test.com','9876543211','Outbound','Open','medium',5,6,1,180,'2026-08-10 12:30:00','2026-08-12 12:00:00','Follow-up on installation delay','Need status update from engineer','Scheduled',2,'2026-08-23 03:55:40','2026-08-23 03:55:40');
/*!40000 ALTER TABLE `calls` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `claim_photos`
--

DROP TABLE IF EXISTS `claim_photos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `claim_photos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `claim_id` int NOT NULL,
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploaded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `claim_id` (`claim_id`),
  CONSTRAINT `claim_photos_ibfk_1` FOREIGN KEY (`claim_id`) REFERENCES `claims` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `claim_photos`
--

LOCK TABLES `claim_photos` WRITE;
/*!40000 ALTER TABLE `claim_photos` DISABLE KEYS */;
INSERT INTO `claim_photos` VALUES (1,1,'/uploads/claims/claim1-photo1.jpg','2026-08-09 13:05:00'),(2,1,'/uploads/claims/claim1-photo2.jpg','2026-08-09 13:06:00'),(3,2,'/uploads/claims/claim2-photo1.jpg','2026-08-10 16:05:00');
/*!40000 ALTER TABLE `claim_photos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `claims`
--

DROP TABLE IF EXISTS `claims`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `claims` (
  `id` int NOT NULL AUTO_INCREMENT,
  `claim_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `order_no` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_item_id` int DEFAULT NULL,
  `customer_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_contact` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `submitted_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `processed_by` int DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `bank_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_holder_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ifsc_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `admin_remark` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `order_item_id` (`order_item_id`),
  KEY `processed_by` (`processed_by`),
  CONSTRAINT `claims_ibfk_1` FOREIGN KEY (`order_item_id`) REFERENCES `order_items` (`id`),
  CONSTRAINT `claims_ibfk_2` FOREIGN KEY (`processed_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `claims`
--

LOCK TABLES `claims` WRITE;
/*!40000 ALTER TABLE `claims` DISABLE KEYS */;
INSERT INTO `claims` VALUES (1,'CLM-2026-0001','V1-ORDER-10ROWS-20260801','8908012210474-A1',1,'Vendor1 Customer','9876543210','customer1@test.com','Approved','2026-08-09 13:00:00',1,'Approved after inspection','State Bank of India','Vendor1 Customer','12345678901','SBIN0000123','Amount approved','2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,'CLM-2026-0002','V2-ORDER-AC-20260805','8908012210436-C1',3,'Test Customer Two','9876543211','customer2@test.com','Processing','2026-08-10 16:00:00',1,'Awaiting final review','HDFC Bank','Test Customer Two','98765432101','HDFC0000456','Review in progress','2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `claims` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `complaint_status_logs`
--

DROP TABLE IF EXISTS `complaint_status_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `complaint_status_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `complaint_id` int NOT NULL,
  `old_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `changed_by` int DEFAULT NULL,
  `remark` text COLLATE utf8mb4_unicode_ci,
  `document_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `action_taken` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `changed_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `complaint_id` (`complaint_id`),
  KEY `changed_by` (`changed_by`),
  CONSTRAINT `complaint_status_logs_ibfk_1` FOREIGN KEY (`complaint_id`) REFERENCES `complaints` (`id`),
  CONSTRAINT `complaint_status_logs_ibfk_2` FOREIGN KEY (`changed_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `complaint_status_logs`
--

LOCK TABLES `complaint_status_logs` WRITE;
/*!40000 ALTER TABLE `complaint_status_logs` DISABLE KEYS */;
INSERT INTO `complaint_status_logs` VALUES (1,1,'Pending','In Process',5,'Assigned to Ravi Kumar',NULL,'Assigned engineer','2026-08-08 10:00:00'),(2,1,'In Process','Resolved',2,'Problem resolved on site','/uploads/complaints/resolution1.pdf','Service completed','2026-08-09 15:00:00'),(3,2,'Pending','Pending',5,'Fresh complaint logged',NULL,'Complaint created','2026-08-10 11:00:00'),(4,3,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-20 14:31:20'),(5,4,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-20 14:31:35'),(6,5,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-22 14:16:07'),(7,6,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-08-23 06:45:06'),(8,6,'Pending','Pending',8,'Customer document upload link generated',NULL,'Request Sent','2026-08-23 06:46:47'),(9,6,'Pending','In Process',8,NULL,NULL,NULL,'2026-08-23 06:48:43'),(10,7,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-23 08:13:54'),(11,8,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-08-23 10:28:04'),(12,9,NULL,'Pending',1,'Seeded sample Service complaint',NULL,NULL,'2026-08-29 12:36:51'),(13,10,NULL,'In Process',1,'Seeded sample Installation complaint',NULL,NULL,'2026-08-29 12:36:51'),(14,11,NULL,'Pending',1,'Seeded sample Sales complaint',NULL,NULL,'2026-08-29 12:36:51'),(15,12,NULL,'Pending',1,'Seeded additional service complaint',NULL,NULL,'2026-08-29 12:36:51'),(16,13,NULL,'In Process',1,'Seeded additional service complaint',NULL,NULL,'2026-08-29 12:36:51'),(17,14,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-08-30 10:16:58'),(18,15,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-30 13:13:11'),(19,16,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-30 13:19:55'),(20,16,'Pending','Pending',1,'Linked to order test',NULL,'Link Customer','2026-08-30 13:46:15'),(21,16,'Pending','Pending',1,'Linked to order test',NULL,'Link Customer','2026-08-30 13:46:49'),(22,16,'Pending','Pending',1,'Linked to order test',NULL,'Link Customer','2026-08-30 14:09:25'),(23,17,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-30 16:00:40'),(24,18,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-08-31 07:51:34'),(25,18,'Pending','Pending',8,'Customer document upload link generated',NULL,'Request Sent','2026-08-31 07:52:44'),(26,19,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-08-31 08:05:16'),(27,19,'Pending','Pending',5,'Customer document upload link generated',NULL,'Request Sent','2026-08-31 08:05:59'),(28,20,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-09-01 03:12:34'),(29,20,'Pending','Pending',8,'Customer document upload link generated',NULL,'Request Sent','2026-09-01 03:16:32'),(30,20,'Pending','Pending',1,'Linked customer dhanannjai',NULL,'Link Customer','2026-09-01 03:18:39'),(31,20,'Pending','Pending',1,'Customer document upload link generated',NULL,'Request Sent','2026-09-01 03:18:57'),(32,20,'Pending','Pending',1,'Linked customer dhanannjai',NULL,'Link Customer','2026-09-01 03:51:10'),(33,21,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-09-04 03:42:55'),(34,22,NULL,'Pending',1,'Complaint created',NULL,NULL,'2026-09-04 04:02:49'),(35,23,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-09-05 04:16:12'),(36,24,NULL,'Pending',5,'Complaint created',NULL,NULL,'2026-09-05 04:18:51'),(37,24,'Pending','Pending',5,'Customer installation document upload link generated',NULL,'Request Sent','2026-09-05 04:21:05');
/*!40000 ALTER TABLE `complaint_status_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `complaints`
--

DROP TABLE IF EXISTS `complaints`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `complaints` (
  `id` int NOT NULL AUTO_INCREMENT,
  `comp_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comp_date` date NOT NULL DEFAULT (curdate()),
  `customer_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_mobile` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_address` text COLLATE utf8mb4_unicode_ci,
  `model_details` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `problem_description` text COLLATE utf8mb4_unicode_ci,
  `query_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status_date` datetime DEFAULT NULL,
  `assigned_engineer` int DEFAULT NULL,
  `remark` text COLLATE utf8mb4_unicode_ci,
  `service_proof_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `access_code` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `send_sms` tinyint(1) NOT NULL,
  `created_by` int DEFAULT NULL,
  `order_item_id` int DEFAULT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  `order_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `assigned_engineer` (`assigned_engineer`),
  KEY `created_by` (`created_by`),
  KEY `order_item_id` (`order_item_id`),
  KEY `ix_complaints_order_id` (`order_id`),
  CONSTRAINT `complaints_ibfk_1` FOREIGN KEY (`assigned_engineer`) REFERENCES `users` (`id`),
  CONSTRAINT `complaints_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
  CONSTRAINT `complaints_ibfk_3` FOREIGN KEY (`order_item_id`) REFERENCES `order_items` (`id`),
  CONSTRAINT `fk_complaints_order_id_orders` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `complaints`
--

LOCK TABLES `complaints` WRITE;
/*!40000 ALTER TABLE `complaints` DISABLE KEYS */;
INSERT INTO `complaints` VALUES (1,'COMP-2026-0001','2026-08-07','Vendor1 Customer','9876543210','customer1@test.com','Tower A, Noida','AIR COOLER IDCCLR40L','Cooling issue after installation','Service','Resolved','2026-08-09 15:00:00',2,'Fan motor checked and cleaned','/uploads/complaints/service-proof-1.pdf','ACC1001',1,5,1,'8908012210474-A1','callcenter','2026-08-20 07:32:21','2026-08-20 07:32:21',NULL,1),(2,'COMP-2026-0002','2026-08-10','Test Customer Two','9876543211','customer2@test.com','Pitampura, Delhi','SPLIT AC IDCACS18K5','Installation delay complaint','Installation','Pending','2026-08-10 11:00:00',3,'Waiting for engineer assignment',NULL,'ACC1002',1,5,3,'8908012210436-C1','public','2026-08-20 07:32:21','2026-08-20 07:32:21',NULL,2),(3,'IDC_1787236280959','2026-08-20','Rajeev ranjan dubey','7050472288','dubeyrajee@gmail.com','Supriya  Road',NULL,'test','Installation','Pending',NULL,NULL,NULL,NULL,'040750',1,1,NULL,NULL,'callcenter','2026-08-20 14:31:20','2026-08-20 14:31:20',NULL,NULL),(4,'IDC_1787236295330','2026-08-20','Muskan Singh','07011249661','comtechenterprises@gmail.com','K225, Site5, Kashana Industrial Area\nGautambuddha Nagar\nKasna','split ac','ii','Service','Pending',NULL,NULL,'iit',NULL,'724839',1,1,NULL,NULL,'callcenter','2026-08-20 14:31:35','2026-08-20 14:31:35',NULL,NULL),(5,'IDC_1787408167976','2026-08-22','test','9891572565','muskandpms@gmail.com','G1-201. ECO VILLAGE-1, NOIDA, UP-201306','AIR COOLER IDCCLR40L','sdfg','Installation','Pending',NULL,NULL,'sdfsdf',NULL,'439643',1,1,NULL,NULL,'callcenter','2026-08-22 14:16:07','2026-08-22 14:16:07',NULL,NULL),(6,'IDC_1787467506528','2026-08-23','PRIYANKA SINGH','08826459036','dhanprigroup@gmail.com','G1-201, ECO VILLAGE 1, GREATER NOIDA WEST- 201306','SPLIT AC ','efrSDGSADFGASDFGASFG','Service','In Process','2026-08-23 06:48:44',2,'SDFSADFSAD',NULL,'611664',1,5,NULL,NULL,'callcenter','2026-08-23 06:45:06','2026-08-23 06:48:43',NULL,NULL),(7,'IDC_1787472834954','2026-08-23','Rajeev ranjan dubey','7050472288','dubeyrajee@gmail.com','Supriya  Road',NULL,'ac is making lot of noise','Service','Pending',NULL,NULL,NULL,NULL,'971833',0,1,NULL,NULL,'callcenter','2026-08-23 08:13:54','2026-08-23 08:13:54',NULL,NULL),(8,'IDC_1787480884086','2026-08-23','Sanskriti Singh','08826459036','sanskritidpms@gmail.com','G1-201, ECO VILLAGE 1, GREATER NOIDA WEST- 201306','SPLIT AC ','RG','Installation','Pending',NULL,NULL,'RGF',NULL,'222147',1,5,NULL,NULL,'callcenter','2026-08-23 10:28:04','2026-08-23 10:28:04',NULL,NULL),(9,'IDC_SEED_1788007011190','2026-08-28','Demo Service Customer','9990000001','demo-service@example.com','Sector 21, Noida, UP','SPLIT AC IDCACS18K5','AC compressor making rattling noise; intermittent cooling.','Service','Pending',NULL,NULL,NULL,NULL,'617760',1,1,NULL,NULL,'callcenter','2026-08-29 12:36:51','2026-08-29 12:36:51',NULL,NULL),(10,'IDC_SEED_1788007011191','2026-08-28','Demo Installation Customer','9990000002','demo-install@example.com','Sector 18, Gurugram, HR','WINDOW AC IDCACW18K3','Customer wants installation coordination for new AC unit.','Installation','In Process',NULL,NULL,NULL,NULL,'317182',1,1,NULL,NULL,'callcenter','2026-08-29 12:36:51','2026-08-29 12:36:51',NULL,NULL),(11,'IDC_SEED_1788007011192','2026-08-28','Demo Sales Prospect','9990000003','demo-sales@example.com','Plot 9, Pune, MH','GEYSER IDCGYS15L','Interested in bulk purchase for commercial premises.','Sales','Pending',NULL,NULL,NULL,NULL,'640962',1,1,NULL,NULL,'callcenter','2026-08-29 12:36:51','2026-08-29 12:36:51',NULL,NULL),(12,'IDC_SEED_1788007011193','2026-08-28','Nitin Bansal','9990000004','nitin.bansal@example.com','Sector 62, Noida, UP','SPLIT AC IDCACS24K5','Customer reports unusual noise after startup.','Service','Pending',NULL,NULL,NULL,NULL,'316155',1,1,NULL,NULL,'callcenter','2026-08-29 12:36:51','2026-08-29 12:36:51',NULL,NULL),(13,'IDC_SEED_1788007011194','2026-08-28','Anjali Rao','9990000005','anjali.rao@example.com','Whitefield, Bengaluru, KA','FRIDGE IDCFRD360L','Customer wants a service visit for cooling issue.','Service','In Process',NULL,NULL,NULL,NULL,'122312',1,1,NULL,NULL,'callcenter','2026-08-29 12:36:51','2026-08-29 12:36:51',NULL,NULL),(14,'IDC_1788085018078','2026-08-30','PRIYANKA SINGH','9891572565','comtechenterprises@gmail.com','K225, Site5, Kashana Industrial Area\nGautambuddha Nagar\nKasna','SPLIT AC IDCACS13K3E','NOT WORKING','Installation','Pending',NULL,NULL,'SDFSDF',NULL,'493524',1,5,NULL,NULL,'callcenter','2026-08-30 10:16:58','2026-08-30 13:14:24','2026-08-30 13:14:24',NULL),(15,'IDC_1788095591702','2026-08-30','sandhya  dubey','7543017992','dubeyrajee@gmail.com','sadasafafasf','Fridge','Ice is  not forming ','Installation','Pending',NULL,NULL,NULL,NULL,'358872',1,1,NULL,NULL,'callcenter','2026-08-30 13:13:12','2026-08-30 13:14:16','2026-08-30 13:14:16',NULL),(16,'IDC_1788095995220','2026-08-30','Muskan Singh','8700462626','muskandpms@gmail.com','test',NULL,'install AC','Installation','Pending',NULL,NULL,NULL,NULL,'030487',1,1,7,'IDC-124','callcenter','2026-08-30 13:19:55','2026-08-30 15:59:56','2026-08-30 15:59:56',5),(17,'IDC_1788105640261','2026-08-30','sandhya dubey1','22222222222222','dubeyrajee@gmail.com','Supriya  Road','Split AC','installtion','Installation','Pending',NULL,NULL,NULL,NULL,'887809',1,1,NULL,NULL,'callcenter','2026-08-30 16:00:40','2026-08-30 16:00:40',NULL,NULL),(18,'IDC_1788162694425','2026-08-31','shivam','9971193899','manoranjan@indcool.in','gorakhjbd cn ','Split AC','ac free service ','Service','Pending',NULL,NULL,NULL,NULL,'322938',1,1,NULL,NULL,'callcenter','2026-08-31 07:51:34','2026-08-31 07:51:34',NULL,NULL),(19,'IDC_1788163516750','2026-08-31','shubham','8009292355','manoranjan@indcool.in','surajpur','Split AC','ac service need ','Service','Pending',NULL,NULL,'free service ',NULL,'032534',1,5,NULL,NULL,'callcenter','2026-08-31 08:05:17','2026-08-31 08:05:17',NULL,NULL),(20,'IDC_1788232354014','2026-09-01','dhanannjai','9891572565','dhananjai@indcool.in','dsfsdf','Split AC','sdfsdf','Service','Pending',NULL,NULL,'sdfsdf',NULL,'812123',1,5,NULL,NULL,'callcenter','2026-09-01 03:12:34','2026-09-01 03:12:34',NULL,NULL),(21,'IDC_1788493375170','2026-09-04','dhanannjai','9891572565','dhananjai@indcool.in','test new','Split AC','sdlfjns','Service','Pending',NULL,NULL,'kjahdslfjha',NULL,'713299',1,5,NULL,NULL,'callcenter','2026-09-04 03:42:55','2026-09-04 03:42:55',NULL,NULL),(22,'IDC_1788494569135','2026-09-04','shuchi  shukla','1234567890','dubeyrajee@gmail.com','Supriya  Road','Split AC','dfwefdsfdsfdsf','Service','Pending',NULL,NULL,'sdfdsfsdf',NULL,'484753',1,1,NULL,NULL,'callcenter','2026-09-04 04:02:49','2026-09-04 04:02:49',NULL,NULL),(23,'IDC_1788581772752','2026-09-05','dhanannjai','9891572565','dhananjai@indcool.in','test new','Split AC',NULL,'Service','Pending',NULL,NULL,NULL,NULL,'347411',1,5,NULL,NULL,'callcenter','2026-09-05 04:16:13','2026-09-05 04:16:13',NULL,NULL),(24,'IDC_1788581931214','2026-09-05','dhanannjai','9891572565','dhananjai@indcool.in','test new','Split AC',NULL,'Installation','Pending',NULL,3,NULL,NULL,'980683',1,5,NULL,NULL,'callcenter','2026-09-05 04:18:51','2026-09-05 05:54:53',NULL,NULL);
/*!40000 ALTER TABLE `complaints` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `couriers`
--

DROP TABLE IF EXISTS `couriers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `couriers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `courier_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `couriers`
--

LOCK TABLES `couriers` WRITE;
/*!40000 ALTER TABLE `couriers` DISABLE KEYS */;
INSERT INTO `couriers` VALUES (1,'BlueDart','Amit Singh','9000000001','support@bluedart.test','Mumbai hub','2026-08-20 07:32:21','2026-08-20 07:32:21',NULL),(2,'Delhivery','Neha Shah','9000000002','support@delhivery.test','Delhi hub','2026-08-20 07:32:21','2026-08-20 07:32:21',NULL);
/*!40000 ALTER TABLE `couriers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `installation_documents`
--

DROP TABLE IF EXISTS `installation_documents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `installation_documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `installation_request_id` int NOT NULL,
  `document_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploaded_by_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploaded_by_user_id` int DEFAULT NULL,
  `uploaded_by_customer_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Uploaded',
  `reviewed_by` int DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_remarks` text COLLATE utf8mb4_unicode_ci,
  `uploaded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `uploaded_by_user_id` (`uploaded_by_user_id`),
  KEY `reviewed_by` (`reviewed_by`),
  KEY `ix_installation_documents_installation_request_id` (`installation_request_id`),
  CONSTRAINT `installation_documents_ibfk_1` FOREIGN KEY (`installation_request_id`) REFERENCES `installation_requests` (`id`),
  CONSTRAINT `installation_documents_ibfk_2` FOREIGN KEY (`uploaded_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_documents_ibfk_3` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `installation_documents`
--

LOCK TABLES `installation_documents` WRITE;
/*!40000 ALTER TABLE `installation_documents` DISABLE KEYS */;
INSERT INTO `installation_documents` VALUES (1,29,'Original Purchase Bill/Invoice','/uploads/installations/2026/09/6e777343f6404711aada3bfbb7b8e876.jpg','customer',NULL,'dhanannjai','Uploaded',NULL,NULL,NULL,'2026-09-05 04:39:00'),(2,29,'Purchase Order','/uploads/installations/2026/09/386cf237ca62402f834ce95792859db7.pdf','customer',NULL,'dhanannjai','Uploaded',NULL,NULL,NULL,'2026-09-05 04:39:00');
/*!40000 ALTER TABLE `installation_documents` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `installation_engineer_serials`
--

DROP TABLE IF EXISTS `installation_engineer_serials`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `installation_engineer_serials` (
  `id` int NOT NULL AUTO_INCREMENT,
  `installation_request_id` int NOT NULL,
  `line_no` int NOT NULL DEFAULT '1',
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `serial_no_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observation` text COLLATE utf8mb4_unicode_ci,
  `unit_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `verification_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Pending',
  `admin_remark` text COLLATE utf8mb4_unicode_ci,
  `verified_by` int DEFAULT NULL,
  `verified_at` datetime DEFAULT NULL,
  `submitted_by` int DEFAULT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `split_installation_request_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `verified_by` (`verified_by`),
  KEY `submitted_by` (`submitted_by`),
  KEY `ix_installation_engineer_serials_installation_request_id` (`installation_request_id`),
  KEY `split_installation_request_id` (`split_installation_request_id`),
  CONSTRAINT `installation_engineer_serials_ibfk_1` FOREIGN KEY (`installation_request_id`) REFERENCES `installation_requests` (`id`),
  CONSTRAINT `installation_engineer_serials_ibfk_2` FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_engineer_serials_ibfk_3` FOREIGN KEY (`submitted_by`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_engineer_serials_ibfk_4` FOREIGN KEY (`split_installation_request_id`) REFERENCES `installation_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `installation_engineer_serials`
--

LOCK TABLES `installation_engineer_serials` WRITE;
/*!40000 ALTER TABLE `installation_engineer_serials` DISABLE KEYS */;
INSERT INTO `installation_engineer_serials` VALUES (2,29,1,'12','17',NULL,'Installed','Approved',NULL,8,'2026-09-05 06:03:59',3,'2026-09-05 05:59:50','2026-09-05 05:59:49',29);
/*!40000 ALTER TABLE `installation_engineer_serials` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `installation_requests`
--

DROP TABLE IF EXISTS `installation_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `installation_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customer_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_number` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` text COLLATE utf8mb4_unicode_ci,
  `order_item_id` int DEFAULT NULL,
  `product_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_no_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `request_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `assigned_engineer` int DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `installation_date` datetime DEFAULT NULL,
  `work_report` text COLLATE utf8mb4_unicode_ci,
  `work_report_file_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settlement_approved_by` int DEFAULT NULL,
  `payment_amount_requested` decimal(10,2) DEFAULT NULL,
  `payment_type_requested` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_qr_code_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_qr_code_blob` longblob,
  `payment_qr_code_filename` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_qr_code_content_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_qr_code_size_bytes` int DEFAULT NULL,
  `payment_proof_file_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_requested_at` datetime DEFAULT NULL,
  `payment_amount_paid` decimal(10,2) DEFAULT NULL,
  `payment_type_paid` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_recorded_at` datetime DEFAULT NULL,
  `payment_recorded_by` int DEFAULT NULL,
  `payment_transaction_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'vendor',
  `order_id` int DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  `document_access_token` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ask_for_documents` tinyint(1) NOT NULL DEFAULT '0',
  `document_request_sent_at` datetime DEFAULT NULL,
  `order_verified_at` datetime DEFAULT NULL,
  `order_verified_by` int DEFAULT NULL,
  `engineer_entered_serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `engineer_entered_serial_no_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_verified_at` datetime DEFAULT NULL,
  `serial_verified_by` int DEFAULT NULL,
  `admin_billing_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `admin_approval_remark` text COLLATE utf8mb4_unicode_ci,
  `admin_approved_at` datetime DEFAULT NULL,
  `admin_approved_by` int DEFAULT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `complaint_id` int DEFAULT NULL,
  `engineer_site_remarks` text COLLATE utf8mb4_unicode_ci,
  `engineer_serials_submitted_at` datetime DEFAULT NULL,
  `parent_installation_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `order_item_id` (`order_item_id`),
  KEY `assigned_engineer` (`assigned_engineer`),
  KEY `settlement_approved_by` (`settlement_approved_by`),
  KEY `payment_recorded_by` (`payment_recorded_by`),
  KEY `payment_transaction_id` (`payment_transaction_id`),
  KEY `fk_installation_requests_created_by_users` (`created_by`),
  KEY `fk_installation_requests_order_verified_by_users` (`order_verified_by`),
  KEY `fk_installation_requests_serial_verified_by_users` (`serial_verified_by`),
  KEY `fk_installation_requests_admin_approved_by_users` (`admin_approved_by`),
  KEY `ix_installation_requests_order_id` (`order_id`),
  KEY `ix_installation_requests_source` (`source`),
  KEY `ix_installation_requests_document_access_token` (`document_access_token`),
  KEY `ix_installation_requests_complaint_id` (`complaint_id`),
  KEY `ix_installation_requests_parent_installation_id` (`parent_installation_id`),
  CONSTRAINT `fk_installation_requests_admin_approved_by_users` FOREIGN KEY (`admin_approved_by`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_installation_requests_complaint_id_complaints` FOREIGN KEY (`complaint_id`) REFERENCES `complaints` (`id`),
  CONSTRAINT `fk_installation_requests_created_by_users` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_installation_requests_order_id_orders` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `fk_installation_requests_order_verified_by_users` FOREIGN KEY (`order_verified_by`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_installation_requests_serial_verified_by_users` FOREIGN KEY (`serial_verified_by`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_requests_ibfk_1` FOREIGN KEY (`order_item_id`) REFERENCES `order_items` (`id`),
  CONSTRAINT `installation_requests_ibfk_2` FOREIGN KEY (`assigned_engineer`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_requests_ibfk_3` FOREIGN KEY (`settlement_approved_by`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_requests_ibfk_4` FOREIGN KEY (`payment_recorded_by`) REFERENCES `users` (`id`),
  CONSTRAINT `installation_requests_ibfk_5` FOREIGN KEY (`payment_transaction_id`) REFERENCES `payment_transactions` (`id`),
  CONSTRAINT `installation_requests_ibfk_6` FOREIGN KEY (`parent_installation_id`) REFERENCES `installation_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `installation_requests`
--

LOCK TABLES `installation_requests` WRITE;
/*!40000 ALTER TABLE `installation_requests` DISABLE KEYS */;
INSERT INTO `installation_requests` VALUES (1,'Vendor1 Customer','9876543210','Tower A, Noida',1,'AIR COOLER IDCCLR40L','8908012210474-A1','8908012210474-A2','2026-08-06 13:11:31',2,'Completed','2026-08-10 12:00:00','Installation completed successfully','/uploads/installations/work-report-1.pdf',1,1250.00,'UPI','/uploads/installations/qr-1.png',NULL,'qr-1.png','image/png',20480,'/uploads/installations/payment-proof-1.pdf','2026-08-09 09:30:00',1250.00,'UPI','2026-08-09 10:30:00',1,1,'2026-08-20 07:32:21','2026-08-20 07:32:21','vendor',1,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(2,'Vendor1 Customer','9876543210','Tower A, Noida',2,'SPLIT AC IDCACS24K5','8908012210481-B1','8908012210481-B2','2026-08-06 11:00:00',2,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-20 07:32:21','2026-08-20 07:32:21','vendor',1,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(3,'Test Customer Two','9876543211','Pitampura, Delhi',3,'SPLIT AC IDCACS18K5','8908012210436-C1',NULL,'2026-08-10 15:00:00',3,'Payment Pending','2026-08-10 17:00:00','Site visit done, awaiting payment approval','/uploads/installations/work-report-3.pdf',1,2200.00,'Cash',NULL,NULL,NULL,NULL,NULL,'/uploads/installations/payment-proof-3.pdf','2026-08-10 17:10:00',2200.00,'Cash','2026-08-10 18:00:00',1,2,'2026-08-20 07:32:21','2026-09-05 07:12:13','vendor',2,NULL,NULL,0,NULL,'2026-09-05 07:12:13',3,'8908012210436-C1',NULL,'2026-09-05 07:12:13',3,'Paid',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(12,'Rajesh Kumar','9876543212','Greater Noida',NULL,'Geyser 25L',NULL,NULL,'2026-08-26 12:58:16',10,'In Progress',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(13,'Meera Rao','9876543213','Faridabad',NULL,'Fridge 250L',NULL,NULL,'2026-08-24 12:58:16',2,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(14,'Sanjay Bhatia','9876543214','Jaipur',NULL,'Air Cooler 40L',NULL,NULL,'2026-08-22 12:58:16',3,'Pending',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(15,'Pooja Sharma','9876543215','Pune',NULL,'Split AC 1.2 Ton',NULL,NULL,'2026-08-20 12:58:16',10,'In Progress',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(16,'Vikram Sethi','9876543216','Lucknow',NULL,'Split AC 1.5 Ton',NULL,NULL,'2026-08-18 12:58:16',2,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(17,'Kiran Malhotra','9876543217','Chandigarh',NULL,'Window AC 2 Ton',NULL,NULL,'2026-08-16 12:58:16',3,'Pending',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(18,'Deepak Joshi','9876543218','Nagpur',NULL,'Geyser 25L',NULL,NULL,'2026-08-14 12:58:16',10,'In Progress',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 12:58:16','2026-08-30 12:58:16','vendor',NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(19,'Muskan Singh','8700462626','Greater Noida',52,'SPLIT AC IDCACS18K5','IDC-120','IDC-132','2026-08-30 13:44:33',2,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 13:44:33','2026-08-30 14:09:56','vendor',5,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(20,'Muskan Singh','8700462626','Greater Noida',53,'SPLIT AC IDCACS18K5','IDC-122','IDC-133','2026-08-30 13:44:33',2,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 13:44:33','2026-08-30 14:09:56','vendor',5,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(21,'Muskan Singh','8700462626','Greater Noida',55,'SPLIT AC IDCACS18K5','IDC-130','IDC-141','2026-08-30 14:10:01',NULL,'Submitted',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-30 14:10:01','2026-08-30 14:10:01','vendor',5,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(22,'VISHWESH MISHRA ','9971193899','GORAKHPUR',67,'SPLIT AC IDCACS18K5','511','526','2026-08-31 07:25:51',2,'In Progress','2026-08-31 00:00:00',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-31 07:25:51','2026-08-31 07:28:32','vendor',25,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(23,'VISHWESH MISHRA ','9971193899','GORAKHPUR',68,'SPLIT AC IDCACS18K5','512','522','2026-08-31 07:25:51',3,'Settlement Approved','2026-08-29 00:00:00','1 ac installation done','/uploads/installations/2026/08/6c5faf58a604461298a285992eae42c5.pdf',1,1500.00,'UPI',NULL,_binary 'ˇ\ÿˇ\‡\0JFIF\0\0`\0`\0\0ˇ\€\0C\0\n\n\n\r\rˇ\€\0C		\r\rˇ¿\0t\—\"\0ˇ\ƒ\0\0\0\0\0\0\0\0\0\0\0	\nˇ\ƒ\0µ\0\0\0}\0!1AQa\"q2Åë°#B±¡R\—\$3brÇ	\n\Z%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyzÉÑÖÜáàâäíìîïñóòôö¢£§•¶ß®©™≤≥¥µ∂∑∏π∫\¬\√\ƒ\≈\∆\«\»\…\ \“\”\‘\’\÷\◊\ÿ\Ÿ\⁄\·\‚\„\‰\Â\Ê\Á\Ë\È\Í\Ò\Ú\Û\Ù\ı\ˆ\˜¯˘˙ˇ\ƒ\0\0\0\0\0\0\0\0	\nˇ\ƒ\0µ\0\0w\0!1AQaq\"2ÅBë°±¡	#3R\br\—\n$4\·%\Ò\Z&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyzÇÉÑÖÜáàâäíìîïñóòôö¢£§•¶ß®©™≤≥¥µ∂∑∏π∫\¬\√\ƒ\≈\∆\«\»\…\ \“\”\‘\’\÷\◊\ÿ\Ÿ\⁄\‚\„\‰\Â\Ê\Á\Ë\È\Í\Ú\Û\Ù\ı\ˆ\˜¯˘˙ˇ\⁄\0\0\0?\0\˜∏?\›4≠7˚\Ú§UßV†1\Óâ˛oÆ¬´J© \‹\ˆ\ \Á\›?¬¨\”\Ë*[dÎß©˙(÷¢˛\≈Fˇ\0ñ;?Îõë¸\Îjä`bˇ\0a7\\ \Òˇ\0\€V4&è®≠,_\kjäBπí∫E\˜V\÷\ZA\È\‰Seø¸˝M˘÷Ü ôVù\…2\·É˛{\Õ˘öo¸#q*`\\\\ˇ\0\ﬂuµ¥QE¿\≈˛\√_˘˘∏¸È´†î\È{q˘÷Ω\\´ô\èè˘˛∏¸\Í6\\–o˘ªˇ\0æÖm`—ÉE\¬\Áü]¸\–o$\‘^W∫ˇ\0N\0MµáQ\‹V¶ë\\Ê\√EµÜ\⁄\⁄\Ê\ÙAaLÉÖ^Ç∫\ﬁ}h\Á÷ê\\√è\¬6-µã‹É\Ó\ıb?X/Uëø\‡u©œ≠=\r1m\·ù5˙\€ˇ\0\‰Wßˇ\0\¬?ßˇ\0œø˛<kG4fêˇ\0\ÿv?\ÛÍüôß&\Õ:[ß\Êj\ˆj7†E_\Ï˚?˘\Ûè\ı¶}Ü\◊v\Ô≤≈ü\˜M\\¶S%Ç$º¥\œ˚î\ÊR>\Ë\˙(VKUím˚Wv6\Á*«≥ß˛ÉSlî\\D	\Ù©<≥\ÈOJvh∏yG÷ó\À>Ü••¸i\‹ºë\ÈB\¬*z_/\€\Ù§fÅOAöG±è˚ø\≈Vë*mîÄ©\‰{Tãn*\ \«N\ÿ($Üû∞äôómXÄ˙S\Ëß\–E;üZ9\ı™∞Æ˙\—G>¥´L.\"Si\À@\\>¥¥î˙7i\Ù£i\Ù©h†|≥\ÈM\ŸS\Êì`†\n≠µ5ñÆl\œ&Ä)ytyu3B\‘\ﬂ∆ÄF\—IözGJ\≈\r\\\”\—O•?\À\ˆ©í:ê\Zë˚UÑè⁄úãV(©Lπß*\—œ≠\0˙e>ÄN\Á÷äëÄé§\Á÷é}h†¢ùE@\rßfäm\0%Q@>¥üç/>¥\⁄\0)èO¶Pç%U5`J—ì\–\ÊùMV5 1xu\œß¥˙UQ\Ú∑z\”¸j÷É\"¢üE\0yviiôßnµ∏fñôövhé¸iy\ı¶\“˛4\≈\Á÷é}ii\€G≠çP}*Z(†ä)3@\r¢ä(\0˛\Z3E2Ä\n(£üZ\09\ı§¸iy\ı¶\–˛4~4îP˛4îQU`\ne>äêO¢ä\0(\ŸE;üZ´\0\⁄v\⁄9\ı©6\nêF\⁄u?e\07i\Ù©9\ı£üZ(´öñõN†få\”sEUÄëX˙Tî\Œ}i\ÈL”π\ı¶”π\ı™∞Æ˙\—œ≠Ss\ÎE´@ß\”3O†T\’‘â@U¢ä*n∂óm%>®\ŸF íä\0è\…÷µ_J≥∂ä\0°˝üBÿΩil\Ìî\Â%ø∫jeÜ≠\Ìîl®\n\¬*E\ÕI≤ù\Â˚P)˛]I∂é}h?.§\€G>¥P≠H¥\⁄}\0:ñíû\ﬂ*Ü<p	\ı\∆q˘\—\Ë(¢üÉ∑8\„¶iX:å£4§\‡å\Zè÷ê∏ \‡éi;\„Ω ∆é}k:\ﬂ_≤∫÷Ø\Ùòd-yßÑ«åàÀåØ?B+@s\–\ÊõMnJeHTÆ2\œ\"£\Õ+Å*R\Û\ÎE[\‘üZãù\’5*\«P}zVäv™F2Ω[á\ÊÖX\ı´¸˙\—Iüz*¨îQG>¥s\ÎY\r\Ë˙g>¥\Ù†CË¢ó\Ò†	—öfh\Õ\0K∏z–¨=j:J\0óp\ı¶\ÊôE\0?4S)˘†4\ (†üZO∆óüZm\0/\„IE\0QE\0QK¯\“UÄQE¨ETÄ\Ó}h\Á÷é}h\Á÷¨¶®}ª\ı©V•˘\0¥\Ó}i¥\Ó}i\0R≠\'>¥P\ÛE2ë\„=Ωh∏©Rô;\ÃX\„yïcE.\Ã\«UFXì\ÿ\02}*É†˛¯\ÔO™∫N©gÆiV⁄éü<w67Qy\–\ÕÜWRqï#Ç2:äπö5N\Ã˛?\Á˛¢ì\ÒÆs\‚>Ω\·\ﬂ\ﬂœ•F≥kRº6Z}π\Û.e`\0ø*±¿\Ï§\ˆ≠\ÍØh∫^°\ \ﬁ[E \€\œ,π?®#\≠π_*óB.Øb\˜\'˘RV/áºe¶x´R\◊\Ï\Ï.\ZI\Ù+Á∞ª\»¿+‹æ£r≤˝Té’µ\”9\Ì÷•\ﬁ.\Ã¢\ÛH9,%N±\„É˘è\ÃS◊Ü\Ì\\∑Ä¶ñIºw\”4\∆\ﬂF¨O‹å$%{`èŒöWMÉ—ù=Hî\’˘sû?˝Y©cN\ı\Z\‘6ü\Ú*d¢ï(∏\≈\Á÷ä)i\0î˙m:¨”π\ı¶füÉ@¢öµ-M¿)\‹˙\—œ≠\\,-:ä)<˚u\ˆ©{g∑≠Q’µ\—\Ù\Û8∂∏ª;ï\ﬁ\Œ2\Ãs‘úv¨9<I\‚ém|%8?ﬂºΩâ?Lµ\\c\Ã+£®¡\Èéi+ìÜO\Z]xÉLKª}.\ÀGUë\ÔZYé\Â\0û\Ê∫\’“¶KópZÖ\Í*n0JóüZèi\Ù©9\ı¢\‡˙\◊;\„LZ_xRˇ\0\Ãué=W\Ï\Ì∑\ \‚X\\&\Ô° }k¢Æw\«…ªI\—\Û\∆\›n\…ˇ\0\Ò\Í∫o\ﬁ\‘R-¯\À\\∫\œÑu]Z\∆\›o/≠a≈µº‹´JœÅí;X~\ˇ\0å≠\Ìû]w\≈V7N78¥”ó`˙s]u\‰0\œo<W1˘ê2\‡«é†r?\◊(∑~≤7\—M˝°£,~w\Ô\Ô\‡_o\ÔWU7\ÕGr≥‘øˇ\0\Ôà.µù G\‚7\Zb\»\Õwn∂±\∆“Ö˚®==Ms:?\«_\r¯áPæµ\”#‘Ø≈º¨ä÷∂RH$Q¸k¥èq]Ç\ﬁ\¬Q\·;â¥\Ÿ\n&£e\"\€L\«i˘\◊\Â9\ÏkÇ\“Ê∑µ\”¸5•\È6&=z\Õ\Ì\Ì (5ˇ\0X\ÚqüSWMß\Ì§I\…|&≠ß∆èjZÑ\ˆq\Íw7v≠≤tãNólM\Ë\Á)\„ΩvöØoØ\√\÷ry\È#\‡\ÓG÷πc£\Õ\·^j∫^ö\◊vzÑ*\'é\–(s*≥\ÂàgÔöπ\·eº\˛õ\‚\rgT¥M6I%õP[•\‚D‹°òqü\\T‘ç)$\ÈéóS;\·\Ëk\Ôx\˜X)ò\Ôu∂ÇéLv\Ò¨G£x?à5\÷j\Z≈Üè\ÌB˙\⁄\–ˇ\0\”YU?ôÆ/¿˛ö\˜\·_á≠\Z\ˆ}6I\–__=ô\Ÿ<¶Vy]3\ÿ\‰ék°≥\vÖ¶\Õ\Ê[\ÈV˛g¸\˜ù|˘?\Ôß,J Ø#ñ•F\Â¯ámyyki£izé®\◊l7\–\⁄∑â}Y\‹m#\Ëkß•\‹Ìåπ\nΩ1ïê´sªt4G>µ&¡Lj\0viŸ®©\Ù¨øçK˙ï®R¶á\Ó\”vä)3E;Å\Â\\˙\—œ≠/CÉ¡£ß_\Û˛sYèpZu£∏\ÎFh\Ï—öni7\rπ\œ¥¡\Ë?4ûú\”r1û’ÖØx\√M\–nÖ≠\ÀN\˜,ªå6∞4Œ†\˜!r@§ì{\–o\Î\Ì÷ó>\ıô°\ÎV \”b‘¥Î§π¥}Àæ5\√+Ø\ﬁVà\ÓJøëCM;2ï¨Iüz\\\‘;Ü3ëä7ì\”\ﬂ\Ù\ÎH|§Ÿ£p\ı®|œõ\>Ω)\ÿ9\∆9¶+fì\Ò™ZÜßk§X\Õyys\rµº#2\Õ4Å1\«,I¿\Í:˙’µ`»é(ÍÆ¨:aï#ÿÉê{”∂ó\Ô∆íì4fêÖ•¸iπ£4\0\Ìß\–\ı\≈6≥µ\›Jm.\Õ%µ\”\Á\‘\Ágÿ±€®\‹?\⁄,\‹b±æ\”\„{\‚DZvè`É\Ó≠\Â\€\ \√Î≥•m\Z|\›D›é®|\›9\ÔK\\\œ\√\ﬂ\\x\À\¬\—\Í∂Kevówó\«+HÖ¢õf\Â\'™ëﬁ∫\\\‘;ßf>Å\Ô⁄ñ±¥G®¯ì\ƒz$êKm{£ºy\‚\‚)î˘rèl´\Ó•jM2Z\Ÿ\‹\›KìΩ¡\€–ÖLˇ\0Jr^Ω?\œ˘\≈&~mΩ˝?\œ\–\◊%\ß\∆3|@¯q£¯é\Ó\–Y\‹]âV[u<)Iù1˘S<7‚´ü|[\Ò~Çåˇ\0\ŸZ%•îl\œP∑reò\Ó≤ü£ﬁ©¡\Î\‰.c≥\ı\ÁßZO∆∞¸\‚∏<]•\Õr∞\Àgqg©\‹iwó\Êéxd\0Ø‘£+c–É\–’èxí\”\¬>‘µã\ˆcihôeQ\Û3ñ⁄àæ¨I¿I\‚éYsr\ÿwV9è¯ö\Ó\Ô\„ƒø\r\›\‹˘\—\È\√LΩ\”\‡#8§Ñ	ø\ŒÀü\˜á≠wõ´¿¸™_\›~\—W⁄¶£ßM°_\ÍêiW∫|\«;HÅ\›zç\÷\‡g◊ä\Ó~\'|j\”>\Í∫MçÕç\Ê•wy\ﬂK†Rm\Ìc;L§{û>µ\Ÿ[(\ 1èTc¶Æ\œH\Í2:z”øj¿\÷<i•höná©O;-v˙\€O¥ùG\Áèz3z(ìZñzÑw\ˆ/sb\Î®G\Âª\∆mN\·+Wéß é;É\\.é\Ë◊ô0wcø•(é\0\…\Ù¨¯ç|_\·\'\\Ü	ma\‘ 	éYT∂\Ê+aX£+µ\Ê’¨cgWº∑VSÜ\r*Çø5\œ_|D—≠|A\·\›\ﬁe\‘/uª∂∑åZ8êD©bÕ∑8#$\Ù»´Vø|1fX\√\·˚g;ú\…l˛µ\√\Íû&\ïø\≈?\œe}¶®∂≥\’IgÂÄ¨\….JìÜ\‡\Ò]î\È\¬w±õìé\Á≠F√ûzu\ˆ\Ê≤<}®6õ\\ﬂ\∆7)Öñ\Z\ÙØ®o%˘˝kõ\Ò\∆M¬∞\ÿ\Õ(ºΩ∑∏∏\ÚL\ˆ∞óH≥\»\Àé¥û.\Ò∆ë\‚o\Î\⁄Nû∑\◊w\Zûôqmº6snVí<¸π\‡\—Nîπ\‚\⁄\–\'%mÀø4â<1\\ˆ\ﬂ@ë\Ÿˇ\0±\ÔØlõ©ç&mü°\ËEw_≈∑¯Ω;\Ù\œ\ÚØ)\?ä<_snn\√Q\›[\Îl5\»n†\"\0N˘|\˜\0t©º\‚okü5πµv\”\Ù\ÿ\‹Ia˝ñŒç!\"<,ô\ŒpOz⁄ÆNrhàMr´ùè¶\r\‚Ü∞íB?â§zî≥πt\œ\„Zø\ÌõIæ\‘t\'9M3S>Hˇ\0ßyáô=Ä$~∏=c\∆P¯¢McT∑âY<\‚;{àdÖ∑õ\»\r∏[âT£\˜œåt˙Wq¢¯Ç\ \Î\∆\Zû£g{i\Àef%∏\nyõ\Â8›úd(\\é\ŸµNç8´\n\Í\˜8ˇ\0Å∂\Ò˘1\Í1>•ßKuu\Î$\«TºèΩw~+\Ònó\‡ù6\“\ÛUúC\Õ–¥âBó&FR\ƒ\Ò\ŸUXü@	\Ì\\/¡v\Ò?î\ -ln\€N≤Py6hû\Ê)G≥}§.ÓÑ°\ÙÆª∆ñrN|?©Efu\Ùõ\˜ñ[0\Ûbñ	abr\Êä\ÒSØg∞†\Ì¢ä\‚)&µA*πC,K∏fDY}GEy\œ¡\›iµ|JµêmYºCq®Aû\È\Ê=≥~Mm\œ“∞¸\'5Ö\◊\«_\nj1\\^ZxO\\≈ŒùjoQ£Kâö\ı¬ÅªÜ˝\—\ŒGnzV¡f\Ò•*\ﬂC>ê\◊L˙∞æèt¨±+_¥ëÇ@\Í\\\ @=Tì“∑XuNú\Ó\…\ÁªG§¯Ø≈öØáº[°XYik{§\œeqwy$g\˜´\Â¥kÖ^ß\Â|˝+≠≥∫Ü\ˆ\ﬁò\\<2¶\‡\»r\Œ2¶HØ=\ÒwäµØ\n\Í^ª\’4Ω:K[çT\È\¬k)ûGA$D≤\·ër	ç1[∂˙_à¥ùJ˛\”K∑\”c\“<\‡\÷\”]N\«jîMÀ±y¿`HÆ\”\˜R7R;˘lN@«ø•/\„\\ó\„]O√∞õ_⁄Ωú\‚Yj®Z\∆D\›\Úúˇ\0˙ö\Ó\Ì\ÊIë7WG\ÂYNCcÆ=k	E\≈Ÿî§ûƒî˙m?i\Ù®(Jóm6üN\‡&\⁄zSi‘πÄ*O∆íä\0\\ˇ\0µKMTß\–≥O®∂üJñÄœ≠G\Àu,)ˇ\0ç.\rÄ˙‘π®\È\’\0¥EP˛4~4îP™;´8ØQRxï\—eQûåº©¸\rIO¶*Éªw5Ñ\ﬁ\\Û\Ãd}\"\ﬁF?{\Ã$©\ˆ\⁄Jﬁ¶”åúvaßQãçUcTE@™*®\Ï;{\Ì\Í\›c¡˙ê3KIœ≠M¸\¬\√0Wß5SX\”µ¥[˝<∑í.\‡í\ﬂx\‰ÄÎ∂Øs\ÎG>¥\ˆw@T±∞]?O∑µV\Û\“!\∆8∂§\€S\Û\ÎM\ŸCnN\ÏSË¢ö`\rMQm>î¿L\”\È6S∂üJ\0uK‹®™Kf˘ZÄ&\€E˙\—@:¸([∂¨öÑ\⁄Ãö≈û°7ùnèvnÑ\0.{ΩA\Í*_äöÖ\Êë\‡[€ªI¶≤OnnÆ\‡\Â\·∂\Û\’fïWæ\Ï9¨/	hZ’á\ƒkçb\◊\√\„\¬˙E\ıª\rF¡nRHßòs®™N\«Øc]ñΩqÆX\«h˙mÆß¡5œíO\˜O<{äﬁ¢èµ\”b>\…?Ü—ó\√zpìV]xyª\’8\"\Í0\‹7Vè>µ\¬¸3\æ•\·{\ÕzIl°\—\Ù\À˘#ö\ﬂI∑π$æ\Í\Ÿ˘Cˇ\0wµw\\˙\÷3äå¨ôhO\‚Ø5∏\‘uM{\«Z\Êìu\‚\'\≥Y\À\”#°7—¥y\Ûü∞¿ÇC\≈zMq\ﬁ7\÷©Øﬁ¥qZ\Èz¶ìqh∞I§\Œ\Z7?\Ôóû\„ät\Ì{1Iv;£ëR$ôÃó\n™¶B1ñ\ı\≈yèá¸o©ü¯ˇ\0KÇ\“mR\ˆ\ﬂWé\ﬁ\ŸG\⁄§#\0n|sﬁΩ\√˙löOá\Ù\›2[«Ωí\Œ\ﬁ8\ÊN\ZBΩ[\Íjñõ†À£¯\√]ø∑UìO\◊!Ü\‚v,ë]ƒ¶#èUt\ÿO°Z™SQ\ÊMé\∂Ü˛\”fäIV{´ªô/n§çv°ï˙™é¬∞<]\„≥\‚≠;\¬Z\\\¬\œPæa\ÍsDZfhÀ¢˝\ˆ\0êΩH\‹W=ˇ\0]â\ÒÉ¯â¶πy\⁄Dõ\Ï¨\„\ GDí¡èT\Â&\Í$\ˆGóA\Ò\≈Z^ßØÀ´ZΩüÅµî∑’§¥M´™\€˘»é\«?pã1=∞Mz\'\ƒ\ÌZ\ÁM±”¥\›1àΩ\◊58¥®.\+©fo¡A?@M^–º†xoGΩ\”,¥ÿø≥\Ô\›\ﬁ\Ó\ﬁCª\œ‹ªN\ÍØ?\√˝2\ÎC±“Æ•æ∫∂±πvr\…r|\ÿªU˛\˘Xåö∑Vú•±<≤8\r\Îö\˜á¸\ÒkC\”u5ºó¡\ÚH4k\ÌG\Ábèò#êèîﬂä∑\‚âæ%K\›I†\ﬁ\ËV∑\Z•ó\ˆæ°q~JB\ﬂx\ı\‡Z\Í\·QxW\Ì\Õq\rå÷â2\"\‹\⁄\€‹∏ä\Î\ﬂ=ÎØ∏H¶Å≠¶Ü)≠e_-°êV¢èLv5r´G¢,è=¯\ı\n_x*\“+¥í\„Ek\Ïﬂà2\€a\Ú&pºëº«ì\Ì[	oÆ&¯A\‡kù@\Ì∫]’§ïõ!àâI\Ù\∆M[h¸-\·yMigm<…∑»Ö≥gà\ÚOOj\ ¯_\Z\◊¡o\nZ]¡\Ê\€Õ¢\≈j\æTî∑!ªsS>_b¨∫é?\“\'â¥â$H\”T≤grUnñ\'†=kKq\Ù¨+?¯sOÇ8mt->åÇ•`Ü\ÚMm\ÓÆ9[°B\Óßn4\∆a\ÎIæên+\–\Êπ?h\ﬁ&\Òü’≠t´V\rÃé\Õ\ˆQóÖ˙ö\È\˜\Z\¬‘º¶_I=\ƒ2]ióRñg∏∞∏hŸæã\–V‘§¢˘àzô^\r\Ò\ˆNßi\‡\›OG_\Í\ƒ\¬\√\»o2\⁄\ÒW\Êo&Oº$˛&ê95\‹Wß¯\…\◊4\ÌOT\Ò°Ø>ñ\Ó\÷]`$È±ü#ìë⁄∫\Ì\Ù\ÎJ2ï\‚T/±\Àk\‘\Ôºz\⁄Óù´E•Z\‹h\—iw`&Èèó4ÆÆûå\Ò\ÕV∞\ﬂã¥m>\ÔA∑\‘,uç.Eí+}GUöCsoÄ>b\„\€\Êä#U«†˘Ns\·\ÔÑ_¿~¥\–^\Â/m\Ïãy3FÖK+rH\ı\…˝N}/\«>3ú¿E∂®\÷\—Œ´\˜§eL˚P\„˝°\Î]h©\ˆè_1X\ÛõﬂÇ\Ò\Í~%\◊5Iµõ´x\ÓØŒ©ß¡f\≈µ\”G\…3xùüvù\„è¯ØR\¨1Iqa≠õB\ ¸\√-ó®\Ïú\ı\'ä\Ùl\“+\ËkH\‚&ö}à\ˆh\Ûü-Ôãºu\·ø\Èz.¢≥\È&YÆ\€Qå\€}™6éDXæ`2¿\ H®>\"¸1\÷<_\‚/\Ë:Ñ:=\Ù˙3\Ë\◊p\ﬁ«º,,˚\…?{-üJ\ı\«˚\‘V´8\…It≥MYúûè\ªG≤\“\Ù´\rVIºFö]ºV\ˆâ~ìç<µmÄ\‡∞\ÛT¸;\\“\Û\¬Z9–¥è˝É\√\À4ØºV@\‹@íª9Dêû≈è&ª∫~\—X∫\Û{≤π\"A•\Èv∫.ìe•\È\Ò˘P$\Òì\˜#^ú\˜5güZO∆óüZ\Á,9\ıÆv\œ¿\Zó\‚Hµã->;ò\Ì\‰ÄdπvL∂=xÆää∏\ QΩòY=\∆7Ô∞≤ ëUeC¯\≈ZI\ÂY\˜≤ü\Ôqü\–T)V6ä\\œ∏ha\Ë~ìC\€g∆∫LR\À4+\’\„\ﬁr#\—[Å\ÌZæ\“\ı)ç\≈\Óôcw?gû\›$ê˚í@’∫}W¥óqr£P\NÅ©\\y\˜:Llm2BLE˚|¡0ü√øŸ¥~VÅc\Z¶*\≈\Úí8\‰gû+°\ŸN¸i˚Y\ıb\ÂFVµ\·∏5[®\Ô\‚ñ]?Râ<µ∏∂\€\ tÉ¡\«cOáCy¢d\‘5	/ø\ŸXÑ)˘kNùKùΩX\“HØ¶\⁄jê§7\ˆPj\È\˜c∏ç\\¶pEQ\ßÖ\Ìº•\Õafã^\‹\›b\ÿ\0ñfpßê°àØ¥˙Tú˙\“sìVl,ä∑∫Eé¨\ˆ/}l≥õÅwjd9\ nH\ÔV\È0i\ÈJ\Ï,s\∆cô\·n±»õ\≈d\Ë^á√∑ìõ+\…SKò\ZV¿céC¸Aâ\Œ=´fï)\Û;X,ñƒï/\„U\˜\Zù*-=)î˙\0)\Ùô•†s\ÎG>¥s\ÎG>µWi\‘fä`>ä_∆óüZ\0r≠-¢ï¿)\ÙQREPN\Á÷õN\Á÷ÄzN\ÕEø∑zz\Â∏üo\Û\Ï*t∏\Íí†©°\Ë,©µ!&ò¥\⁄Mˇ\0\œ-úsé¥\ÏS\nZICô#Ñè˚\Ïp?:lwJªê\Ô\\\„*r3úQfM\«\Û˛œ∏§ÆY\Ò\ˆ^4\\ÓÖhb\‘-nÆ\Êb~e\ı˙ä\Ë;\ÿ\Ù°¶∑((\Á÷ó¯∂ˇ\0ßza`†¿p≠kÄQE\Ó •¸i(¶π\ı¶C9Yº±˝¸qN¸jHäÄ%¢ì\Ò¢Ä<ù∑R\Û\ÎI¯\—¯\÷%	≤ùœ≠˙\“~4∆¥üZm/\„I@¥\Ô∆íô\ÁG\Á\«\ı\Û§í<ç\Ã3åÅﬂöv\Ù\ r;ˇ\0ì˝G\ÁE\Z\0\‹JJ}2ç\0vi\l3F\Ã2ª∫T^üL˛¥≠∫#Ç§L{g˘S\Ûy?Ö¸UÉm¸Qc®ZO\'èüSºûQy/‘ø\Ó$çà¬®^8ØA\ûãˇ\0œÑt-;õO±ä›õ’ï~j\’\Û0\ ¯\È¸C™˝	\Ó)0Y˘8≠ßSô(¢é\‚S\ÛQ•-bEs\Î@Ω¶\—Lc©˘¶s\ÎE\"u$V4\Âzfh\Õ\\ó4¸\‘*\√÷ù¯\–\"L—öfh†	sN¸j:v\·\Î@S\ÈâNZ\0Z_∆è∆úä=h\0¢ùE\0	R\Û\ÎMßP\Ì>î\Íu\€ﬂ•0œ≠•˙@˙(†s\ÎKBS®\0ß\—E\0;üZ9\ı¢ä\0U©í£©y\ı†°iŸ¢Ä\nóüZm;üZ\09\ı•§ß\ÊÄR•0|\›9ß´\ÍqTù¿r%?h\ı§çÅ\Á<S∂üCE¿6\nu&\‡z\Z^\‰wj@(£ìåsE\0QE\0â®^xÜ\ÎUû\◊L∞≥¥≥ÅT˚˘ò	ú\ı\Ú\—2@≠∫Ç˚R≥\–\Ù\Î≠OPò\√ae	∏ö^\Âx›è\‘”É\÷\¬j\Êwá\ıâ\ı	5;+\Ë\ﬁ˚OîA4hr@ É\Ó?B*∑ƒçV\˜H\F†t\ŸEΩ˝\ÎGc\…˚9ïº∂ó˛˙äÇ4\ÌB-2\ÁQ\’bXµùj\‰\Í©»∑#É˛\Ÿ∆£\Ò≠´\€X.≠§∞ºEí\'S\ÊG\Î˝”û\ƒV\⁄)lI\…¯O\·mØÜtX¨øÆjbÅ$ó¨äøÄ5=\«√ù.\ÔX“µ	ouiüNví;gæê\ƒ\‰\Ù\‹dÅPj\◊\ﬁ\”\Ó/E\“j:5î-<©3û◊©\œz\È\Ù€¥\’4˚[\ËXn\"IF\ÓªM]IN\◊]E\\\‰|mπ©¯\√N±≥\Ò	\˝Éi\Ï§[\Ã\Û3`è®P];≈∫?à4\Õ)¸[∂70I$ObíL\≈zÉ\œj\Ó\ı-\ÀZ∂6\˜ñ\Î<@\ÓP\ŸüÓ∞™\ZWÑt\›#Pk\Ë\≈\Â\Õ˛\œ)./Æ\‰∏h£?yWsì\ÎZF∫åD\„s\Õ<q\‡=Z\◊Pü\ƒ\⁄÷£äl°1gq\ÊF–¶\Ï+\ÌﬁÆôm\Ù\ﬂ¯ª\√v\⁄™ÉS\Û|\Ì>∑ÑâWpìi9w\Èö\Ó\ﬁ5ö\"ï\—\»6≤∫\jçùûè\·\Ô5]6\ﬂOX°wô\Ì¢\ÿŒÉíÑå\‡\ÈJU˘’ò˘Q\œis.π\Ò[ƒóÃπ]\÷\ﬂFá\⁄V_6o\«=kk\\\÷5´[´+\rLé\Í\Í}\“O®^7ókk\Èª4è˛\ \ÛX_\Ù˘\·∂\‘nI7˙¥\“\ÍW,z≥L˚ˇ\0\Ò\‘˘J\Ì´\ní¥¥)#ù˛¡\÷o¥<Qr¸\Û”≠\„Å?\Ò\ÂsN\”¸!ü¨¶°˝ß´ﬁ∫\ƒ…≤˛\Ù ø\\c≠t(\ŸI\‘lvAE;üZ9\ı¨Ü34fü∂¢´ZÄ\Ï‘ê\‘1\‘\—p\‹\ÒJ\‡KE.}\Ë¶íyã\Ê${ó\Ã}\€S<ù£-Å\Ï9>î\Ï8\Ôè\«“º\˜\‚Vªk\·Ø\Z¸=øºîàcõP‹†_˝\0∏xñ }H∑\·≠?UíÈµΩ^\Ú\Í)\Ó\‚\n∫F@ä\œ\‹WKz\‚©\“j\n}¡J\Ó\»\ÈÉd\‡r})zåéGˇ\0_Œ∏ˇ\0â_4ØÖ∫-û´¨$\Ôoqvñ¢;T.\ÏH\Œ@zèŒá¯´\·y<4\ﬁ\"¥‘£æ\—!‘¢\”..†åÖÇY\Z5´vÀñ\Áµ%Fn<\ÈhÒΩØ©\◊\Áøj_z\‡º]\Òü\√^\Ò’èÖ\ı´â-%πètóå7Al\ƒe_g˚W_©jvZFõ6•qu\r∂ü~lól~@ü\ﬁ\'¶9\ÎD©N\Ê[èö/fhCõpà9\Áæï\Âû\^ô\Ò*Oƒö\À\\}¶\Ê˛\‚:kyô\∆(ú∆åÉ¶KH>ÜΩ3Mºä\ÈlØ-\'é\Ê\⁄`≤\≈4.gR8#>ï¿|?\‘U|;\'á\Ïò\rB\ÀW\‘\Ï\‰\Á˝Lky$Å\€˛\È\…˛\Ú˙ä\ËÇqÉ≤\‘\ŒRπ\◊xf\Í\Ú\Î\√\ˆç®ïö˙=\–\Õpß7ñ˚V_¯Pq\ËkWÆq\Œ:ˇ\0ü\ƒT1¬ñ±ìà\–gô\‚\ÕJ˚J\\Õ\ı\Óõf5\ÎtWé\€8\Û>d\œ\◊ü•ru6F\Œiø\Ú\—(ê\Ìf\«4\'˙’§ß\¬~&\Íæ ]Jkò4-/S∏\“üûSM,\Îdw∏\ÌV~\›\\\ﬁ|?∞˚\\\“]477ñ\Oqí\“\⁄\«t\Î	o¨a~oB*ÖÆï®\Íü\r¸qe°M¶Ø{Æ\Î\"dl#]∫[\‘÷üÑ|Q`\”Z¯Zm6\„√öµ•Æ!\”nê2Fø3E \‚O\Ô63Å…Æ⁄ë\\ç#æ\Â\ÕS\ƒ\”iû;\ŒÜm\’\Ìu´[\Ê7\0\Û∞*>=\Úk†<u8Æ/\∆$?>L\ÿ]≥\Í®\ƒ\ÒÖ˚	bO∞¡¸çu\÷wP_Z\€^\Ÿ\Õ’≠\¬éH\ÿ2∫êHe#ÇücXNü*ã∂å|\⁄ÿõ∂s\∆q¯˙Rw\∆y\ÙÆ^\ﬂ\‚ù{\ÒO\nGŸºP\–\—	6\‚m•¸ù¯\∆¸qú\‡\ZΩk\‚\Õ>˚E\÷5+ñ\ˆ\ﬂIû\Í\ﬁuÅˇ\06\‹\‚UQ¸\\å\ÌR\·(´¥4\Ómz\ÛK\◊5óˇ\0	Nò\⁄.ù´}π!”µn\÷\◊2ê°¸\ÓcQû§ûûµ.©¨X\È7Z]∂°t∂≤jwB\∆\—r%úç¿gﬂ∞©≥∏\—wß^)\›qÉ◊•e¯ì\ƒæ\—nu;¨∂Õ±G\Î$≠\˜QGv<\‡Ms\ÒÆµ¨\Î\ÒNïõÆX\È\Ò\Î)\ˆG\ﬁ%≤f€é:0aÉ\Ëx´T\Â(\Û$.e{\◊\„@˘∏5\≈j|\'eßY_ùGœµ∫∑[£=•ºíao\„ó\˜`w-åWj\»T\‡p@dx˘\» éπ“î%âöñ\¬\—G|gú\‚é}k0∞Tπ®π\ı£q†,MKüzãy•\Õa\Â∂\ı\‚ù◊•D™\ﬁM¡à\Ïï`ê«ûF\‡õ≤kô¯O\‚Ÿºy\\«\¬\ﬁ\"∏\n∑ó\ˆ)$\ÍΩ™Hq˘Ç>†\’[NnÑΩé\≈^§\ﬁj“£\Zê\'\‹})\Î(\Ù™b\Ú∫6\¬X\Õ»è\Õ0\Ó\ˆgn\Ïu\∆xœ≠Kû˘\„•-∑rëün3\∆zgΩQìR¥áS∑“§∫â5ò\‚+Vp%d\¬\ı ßÆw\∆FiºQ\\Î\Ï\Û∫1\÷n\r\ƒJxíg)p}É\Ïˇ\0æó\‘VëãìgfÜ§Z™¨j0c9\„÷£»´\ÎW\Ì§¯U‘ëwµçï\≈\ )\Ë\ﬁ\\[á\Ú5ô\\”≈ç„èáæ\ÒUÜ]B\Õ\'ñ1\Œ\…sµó\€è≠?\«Dˇ\0\¬\‚¿áh∑˚}ˇ\0\—\ﬂ¸\Â\\O\Ï\Â∆ï\‡ª\Õp\∆+9m\Ó†\»ˇ\0ñv±\\.=Éô\’\–\◊di\'Aœ™fNVü)\Í\‘¸\‘3\\Eo\Z<≤$H\ÌµY\ÿ\0«¶=M<|\›9ˇ\0\Î\ÙÆW¨U\ı&•Jå1l`g#\"ù\È\Ô\œ˘¸\«\ÁIÆQì\∆ß˘\Œ?ù*∞aï9\«\œxª\≈\√>\◊5X\≈\ı˝à\ˆ\ˆÅπ7í\·`å˚ñ \„Ø\"≤¸	´k\˜⁄áÖ¸Mw°\‚->(\ÓÖ\Ì≤lKõw^XUn°≠U)∏{E±<\ \ˆ;}√É∏`\—◊°\Õrüºy\√_\0\Í\"í\›\Ó¸π#Üh\ÿ:iÖ_\»èj\Íò\Ê)åV|Æ…æ•_òdr=æ∏˛téDl™\Ák0$+pN:\◊\ÒO\‚e∑\√\›.\¬yeoÆkS{∂∏X\‡‰§óíyD¡{∞\«Zø\·œÜ∫FÉ©[\Í´-Ê£≠FIóR∫ú¥ì±^õ~\ËØ≤j\nr\“\‰\Û]\ŸL}3⁄§V	\È\≈s>\ÒU«Öt˛Õµ˚wàuYø≥t{>\“]∏ªz\")ûÄMbxK\«I£¯[∏\ÒFØm{®xV\Ê\„O÷Ø-@+Ω%X\” è\ÃRT¶\„ÃÜ‰ì±\Ët˙ä*≤ê\ ÀπH\‰\∆r=±R\÷:ßfWKèßs\ÎL\Õ;\Ò†B\—EC\ƒ!\”¸+•æ°´]%Ω¢»±e\œ\Œ\›9\ÙIæ#xb\Á^¥/˝\ÿ\Ê\‹J\Ÿh\"ö?.X£ï7\⁄\Èï\‹;\‡\”\‘]®è\Ô*(?®≠\"\„\‘xºw•\‹\‹}æ\ÂΩoc3è\—j_¯I•;|≠Yõ˛\›<ø˝\rÖj§í´}\ˆT\Ù\œ¯\nw\Õ\Í\ﬂ\˜\’W4;Øs˚Yo\ı>ªo˙\Èunø÷£∏º\ÒÖ’úãea§i\◊[l◊óM>\œ¯ S[˘oZrR\Á]Ö\À\ÊC•\√yk•\⁄G®\\Gy®\Ûqq\néI\\/P*\Á\„M\Õ-cr\≈\œ˚Tº˙\‘p¨´ªsÉ\ÛzTú˙\—p}k;\ƒ:\rßât{ù2\ıY\Ì.1º)¡8m\ÿ˙Vè>¥s\ÎB\”P9•\yf\Õœà5À§ˇ\0ûjHˇ\0TAIo\ˇ\0K≤íi¥\Èµ\r6\ÊoΩ$wM ˇ\0Å	3ü¬∫m¥ªEW5\≈cX\Vï\‚+[5à•’°∂R≠Ãòén\‰\…\Z\¿û¬∑p[%Ç\‰\„#)\«`AO\⁄=h•\ÃﬁÄíE:äùG†\Ã\Zlë£\∆RH¸\‘`C!2û∆•¢ù¿â\"∆ë¢™¬™∆ãÄ†v\Ï\Z}\\KAò4S\Èî\∆s\ÎE˙\–¯\‘U#\“*U\'`´E-ƒµ ;4S\æîUïc\Âœä~\r/\ÒGÄñ=Fm\Z\Íª¶µΩçCf+\∆OP\≈E]õ\‚zh:}˙¯æ\ƒ\Ë\⁄\Ìå\\Iπ\ﬂ\r\ÚØj\›%\œ\˜:ä\ÓdX\‰Xã*øî˛laá(\€v\‰\Z≠´iv:\ıúñ:ù¨W\ˆÆ6ïôsÄx`P≠\„V2äÑ\ˆ2\Âi\›W\ÒÅ<9\‚\‡MS[\ﬂ}\‡õòØDˇ\0fR“£\À\nyÅ–©}k\»|\‡˝W\√rkæ\◊-o¥ˇ\0\n¯\≈c\◊⁄ûÿë&V1\Ëí\ÌP6ûk\Ë\ﬂ\r¸)\∑É\ÓM∆ì§à&\⁄dï•T˛\Ó\’n8Æ¶\‚∫èÀû$∫â[à\Ê\–˝Cs˘W°z£ete\Ï9ü1\Ú\˜\≈Çû#\ÒWä\ı{\Õ+Zè∆ãqfØ≤]F≥ùë\‡F\√<ú˙W®K≠Xx\Û\·ﬁü\·?¡};\…gie?⁄≠û!hâ¥Hd,:êZ\ı{x¨\„X\Ì\Ì\„¥Lm\€nª\Ù\Ê¶[áoºI\ıc\…¸xÊ∞©èuTTó\¬8\—\Â<\Œ\ÛP∂¯K\„\”4\€gõ@\Ò42M•\ÈP&V\rB2ÇX\„\œ+®Yø\Ÿ \”l|=\‚\ﬂx£\ƒs\È\⁄u¶∑\'â\ƒw≤]ôqX^.VH üºÖvèºVΩ\„N¥ºø≤Ω∏∂In\Ï|œ≥L\√˝^\ı\⁄Hµc˚‹ö\«\Î;Èπ£ß~ßù¯c\∆\ZØÉt\÷\–<dó\◊\⁄≈ú¨©¨Y\⁄<\÷⁄ÑE\ÛÆ\—\Ú∞^=*˚x\€XÉ\≈\⁄π\“d\“¸%®<ño{x<πÖ\”F^#≥¯ï\œsä\ÌVIx√øw\Ê\È˘äl∏òbE2*≤æ\Œ,9V\ËA¨]Hø≤Rç∫é\Á÷ï?\÷)\ÌM\ıÊóüZ¿\–\·\ÙI5ç6\Œ˙\ÔH≤˛\’\Ú\ı\Õb;\€\r\‚d{∑x\Ÿ	\ÍpA\„µfxöˇ\0U\Ò\Ê•\·\À[/\r\Î\ZeÊù™C®\rORÖ`é\ﬁ5?æåÕº:\Ò∑ΩzS\Ã8€íK|øyª±\«sCXµt{gv\Ì©è)\Áˇ\0º≠¯ª\≈^ìJñ;m.\ŒK\»\ıg\√\«±∆ôOV\⁄$\*á¡wV\ﬂtX¸\'´˝¢=;Mû_\Ïªˇ\0)ûm]\Ÿ\„G+ú2ñ+é¬Ω÷û≤<j1\¬\ÙU8 ´\ÎpP{ \Â\÷\ÁèxB\Ô[µ\÷Ô†∞\\›˛£n|Mw≠\⁄j[\rº3,±0ç8\‡+1zWG˚?\«.õ\‡^$k©∂∑©K®ƒù·Æürê}T\Á\È\Õwr\»O\Òm_ß\ËCoV\Î2\≈\nB\'ïÆ%\Ÿ\›\€\Ô7÷Æ¶\'\⁄Gñ\÷a\ ye\Á¡-OT\\‘~π\Òv\⁄Vä\Ôq†˝û#∏L\'\Û!3˙ÑOî\n\Èn<\'™x\ÀT\”5/Monöm\◊\€mt\›%ôG\⁄3\ ~cÅ¸\"ª:+7^MX=ö9?à\⁄£\‚+]}28n.¥≠b\rH\⁄\‹8H\ÊH\˜\·I=z\”|\·˝^\«\«\Z\˜â¸@,M\Ó°kikŸª0ÜÀ≥C\Ûv,A5\’\—J5\Â\Ú£NE{û_\‡_¡\\«‡∂£ß\ÎÇ\ﬂœ∫é\Ë_\˜og¬Ñ˚\0Æ´¡˙.°o\ØC\—\Ó\ÁóN\’±!µödº2àpO<\Óä\Ën¨mØºü¥\√\¬\≈\'õ\ZÃ§™∞˚Æ∑°©ôô\∆\‚y•R¥\Í|A®\Ïch>è√≤¨ë\Ízµ\Ë\Ú|ñK\€\√*9˛\ˆ1êks\Ò¶\Êå\÷é¸h¸iπ•†Wö3M¢Ä∏\ı,\»\ÒÉÇ\»Sw\’v\◊\]tè¯N˚\√6:µΩ›Æá©\\Z\€\»\”.Z\"enæ≤2˝Aﬁ´J«É¿˛Ü\Íkî\\ˆò≥\ŒŸño≤Ø\'\◊hj\“J.,á©ª\r\ƒWà•IH!?\nù\rQ≥\”llµÆüihXm>D\nü“≠\÷z\„uxd\”>5xgP\Âm\ım\˜I,O\ &äHßE˙ëøªO°§∑¯üeq\ÒY|:íB˙döc§W´\»}I$˘†W˚§˘}á9ÆóZ\–\Ùˇ\0Xã-N\÷;ªUq2E&·µ±\‘0\‰eXÉ\Ù®\Ó<5£^hQ\Ë≤\Èñ\Ì•G˛™–å,g¶\Â#°#©&∑å©Z\ÚD\Ú≥Ñ\÷\¬\”\ˆò\”\Ô.ú&ßã{{Uv¬≠ìi∑k.A\Ón\Z\ı\≈oxûGÉ\‚\◊\√\Ÿ7*\‚\◊WÅ\„ÏÆ∂\Ò\ﬂRè\‡}+kG\^Å°§f\œE≥GL~˘êº£É1\ÈSk\Z\Zj\⁄«áØƒõ%\“ngô	VX2\Ê*•Ví∑Ea(¥s3x\ \ÛG¯ù\‚˝2[[\›U>√¶>ècmY6\ f;˙(\»Ps\”#÷∫?¯\“/€òn¢m\'[µë¢∫\”.y±0lO\Ô.;\Ù≠%öD∫¿gœñ©\˜ˇ\0áwL\„4öóá\Ù\Õ{h‘¨-\ÔJ˝◊ï\Ò\Ù`G\ÎQ\œNJ\Õ©\À|x\Ò2¯w\·.Æ´0Ç\ÔXt\—\·òs≥\Ì+∂=j\ÿ\˜a\ÎP|Ωk\œ\n€¥™R\Ê?\r\Ë∂wH\√ó\“j\Úé\"kr˚\·Ü5+1\È\ﬂgí9£∏Ü\Í9¶ÜDn\˜~DRxG¡\Ü\Î:\Ù\÷\◊2]\⁄jŒ∑r\…t¿\Œf\Ú§é6ù\Ó\‹wj\ÌU®¨+ß\‘\≈\¬Nw<\Î\ƒ\ﬁ8˝®°≥\÷dk\ÌM\—\‡í\€Kìz\∆\€\„q+ÇΩ\n∏^Ω2+®\“\ÙΩv˚·ûßa¢\Í3Ku§\Î\”6ë4Ø\Õ’µΩ\∆‰çèp\À\Úg◊ä\Ï5è\Èû πä\Ó\Ó;ÑºH|è:\⁄\ÍH\«\◊\∆√Ωji\ˆ6\⁄]çΩïú+kgmóqÉ¥\Ù\ı$∑$\÷U1*Pä]T\Ï\Ã|N“ºU}¨⁄§WZU÷öa7\Íq≠πÀÆN\–¯\‡æïï\·t÷æ/k˛#\“\ı\ÕGB:ZŸ¥\œ35ª]º€èíO°TGL\◊eq£\ÈZî\¬k\Ì*\ ˙aè\ﬁ][$Ñ\„\Í\ÎZÑé5é4Xì9⁄Ä*\Ó\ı¿¨•Rn(|≤<[\∆Z´u˚Li\⁄çt∫fù}ek\„\rB\‡F,∂\Ì%ºgi\ıê\∆q˛\Õox˚C◊¥O\ÏØA\‚wí]>e¥ªöK≥úÕâ\\\‡\ÚP\Úz\Ë\ˆ+\‚u±\ÌRK(\Ù\„pÜìz®ˇ\0Årh\◊\Ùµ\Òáu].F\ÚE˝§\÷\Õ \⁄]6\Ó\‘7\"∫~∑¨RZ{=\Ÿ\Á\ﬁ#\≠\Áâ~0xK√ö\Ê∞˙ŒÉ•\ŸM‚õãF∑¨≤\«$p[£\€21¸\rz›∫õªÄ	\À3uÆ#X±æ\\˜ãt_ZZ\›j÷ëi\ÿw±¿™f¿ï%IïzûG5\—\Ë∫\È‘§/\rï\Â†_ò=\‰\r\œ—Ä¨´œüñ\€#H£∆º|a˝†º]\‚}R\›.t/Aéìm0˘s<K!\‘\ƒ\ÔüVØhìZ\”-5ªOõòc\’fµí\È,’≥\"\√2\‰uëœ∏ÆV/Ñ\ˆ\Zn©¢kz«áÆ/˛KÅb\Ò\Ï#,¯ï∫\ÿ\◊4ø\ÙØ\n¸^\U\”\Í7⁄§⁄Öæß≥jni¶	*úu\n=\ru÷ï,U≠+(≠îy†¨Œ≥\≈_h∞¯è\·ØΩΩ\Â\Óëc•\ﬁZ†∞∑i\‰Ç\‚Y\"\‹˚\ÛF\nÜ\ÌÉ^w¶xWT\Ò%ø\ƒOO\·K˝	|q\‚a}w<ä<´]+e∏%\‹\e\"\'˘z\Â´ﬁîï\\\Ù¨˝j=r\Î»ãHø≥”£cõõõà^w¿\Ë(çsSƒ∏Gñ\≈ ü6∑1|3\Ë:∆Ø\‡\Èßkë•\≈›ù\Àô\Ï\Âb7∫8+\ÓÆ\”5Å†xF\◊\√⁄Ü£©}¶\ÎR÷µwZç\„ÇÏà¨5\‹[\…5π\\µd•;¢\·}ò˙}2üY:ñìüZ~h¥S≥Fi\‹ú¥\‹\”\Ít\Zr\‘8◊≠MLS\Èî˙V\Ztt\ l8áíI˘®Z)Ÿ¢ò\r°i\‘R∏°Kdí\◊£i\Œ0sªoN˛üZlUfç\√÷ñfKuå\ \ÎêïB\‰\r\ƒu◊®¸È®æ¬∫\rß“äI$XFduåm\›\Ûq\Î\Ù™\÷˙•≠ˇ\0¸{]Cqˇ\0\\§\r¸è“ü$ªic\È\Ô\»¸:ˇ\0*e`¯\√Zº\”n<7m`c2jZô∂ú2ú¨+ª[√ê\‰ë\Ó)J.+P\ne?ölø\'\ﬁ˘y\«>æîêƒ¢ä9\ı¶œ≠˙\—œ≠˙\–wRèº¥˝î\Ô.ÄE3i¢™\Â\\\ÚJ(£üZïµÜ˙\—œ≠Äx\'ß˘¸\r dú\nZ	y>¥âK\ŒH\œ\"ì?\ÌSZä\·¯\—¯\“RfÅ\‹>µWP\‘-t\À\Ó\ÔgK{;x¸\…%v\n‘ûïg\ÒÆ_\«÷´¨I\·ù˛t\’51%\»<n∂Å\ZYG\–¸´\ı`;÷∞äìHNVFáÑºYßx\€\√\ˆ˙∆ì$≤Yªº`»û\\ä—∞ ≤ûÑ©ÑV\«\„X^â\‚’ºTWk6£\Î¥\0ª\⁄\⁄\"\·Tt\‰\»\÷\‡˘∫sS$¢\Ïá}./\„G\„M\'x•®$w>¥s\ÎI¯\—¯˚PUÜJ	8\'“ë+?˛M#˛\Ï\ÌK?Ìù¶O∞yã\Ê\7∑9\È\œNï\Ã\È\Ó2)ÿãè\Õ®V\‚&∫6´*ëúa7\Ï\‹v:\„q=2@©3I\›wLßn¥\‹\–]¬ä(\Õ\n(ßn¥\0\⁄viπ¢ÇfñôN\Õ\0;\Òß%Føz§J\0ì4˙ä•\‰\Á8\ÎR\˜∞.\—I\ÈEí\Êå\”h§¥6è¥oˇ\0f≠\∆G≠U\ÕM π<\n`Z¢ôª=9ˇ\08ß\Ê§-;\Ò\˜®Íáäµ\Ëº+\·o]û)\'áJ∞ñ˝·çÄ‹±ç\ƒgﬁöM¥ê∫\Z©\ÿw©®iZî:∆ìß\Í\‹\€\ﬂ[Esˇ\0fD\‹1\Ì\»¸\Í\ÓhwA•ÆI¯‘ï\n\”—™\ƒJ≠è∫ÿß\∆Y∫öÅ)\Í∆ßQÿü5CX\˝áà≠aáQ∂3àd\Û!ëc\ƒ\≈v±S\ÔW*c¡ \jì}	\ÿvi\Ò\‘9£\Ì1\«$Q≥™\…(c\Z}ø{æ;˙T\ı\ﬂ>¥µ\ÍTz¥2\\”≥QS\„§\"O∆ñôúÆG#¶i\Ÿ\‰ç‹ÇA˙é¢éó≈£4ùN…¶ñ\0\‡ú\ZCööπm3\ƒWwˇ\0µ˝[u[-7N±πÇ\‡ôöo3 è_ì\ÙÆÆ\≈<\Î®\–˝\“\«\'∞\«_\ÁW\ ”≥£ö∑\Ò\Êì{\„\À\œ	¡,ßS±áu√ï˝\ \»@c\Z∑B\ $u\0ä\Ë\ÀmmßÜ\∆qﬁºgL∂’µ\œ¯g\ƒ\ﬁí\ÌΩs\ƒ7W,ŒøªK{ãâC;\ˆ\"Å@\‚Ø|0÷Ø<A\Òó\‚U\Ïó/%ó˙=≠•ô<B!í\‚@\ıs}\Ò]3√∏\Û8\Ù#õo3\◊i˝¿\ÓNUädùY£ëdUfB\ \ŸÜr>£?CP\rZ\ŒMZ\„Jäx‰ΩµÅ\'∏ÅLh\„)üB√ßØj\‰znhhz«•\"+¨í≥6Uæ\Ë\«Jä\ÃJ\ Zl=aVy\ı†@<öx˘Å#ê:\÷àµ≠_Kñ\∆=7\√\◊Z–üwö\—\›Ep\„ß\ﬂ\"≥\Óµo\ŒmE∑á4´5í\Í8\‰í\ÁR\Ûåpûß\nº\’r\Èp:˙3M˚Ø¥r=i*\0\‰\ÔØ5ØxãV\“4\Ìa|5¶h˛Z5’§=\Â‹•w2Ç¸E˝\–GS\≈Q\–~‹¨>oâºO≠xÉSõ\Êí8o\Z\“\÷ˇ\0ûq∆Ä\ﬂY≠i∂^Z\Í_cø{\ıeÑ]i@˘\·ºW¯´úµ\‘<i.Øii§\Ÿ\‹^\È\Ì2¨\Û¯Ç\—lÑQ#\Êv\ˆª\‚\ﬂ/∫edtQ¸=≥)≥\’u\€6\›¸\ZÅaˇ\0èÉ\\ØÅ<¶¯´P÷ºK\‚+F\‘\ı∂Ωí\ \–\‹\Ã\Ït˚X[di˚°õhb\Õ\ÿ\ÊΩ=AG\\\Z≈π\Üùq®Myó∫m\Ãƒ¥≤i\˜#!=\Ò\–\Z\Œ5•fõ/ïYÆ|\“5O¯K\Ù[∏$\‘uØ#˚F\ﬂVöfí\·ï˛\‰d1!}ÖM•Z¯kH\Nåö1∑ãƒ§\€\√ûüIeïôCÜÖI¬Ä[µz¶É\·˚\rGr4\Ëdç\Ó•\ÛÆ..&ißïˇ\0º\“78îU\À{X`ôû\ﬁ\ﬁecñx\„\0ñ\ı$ˇ\0J\ËxûefG!\ ¯íF∫¯°\‡\›5>u≤≤ª‘¶e\‰ïÖ	\Ù\œœè]ß\–÷Üπ\‚ã˚}C˚+B\–[[\‘\’k©\Ó•˚5§!∏§920¬º\÷wÜ›µ_à\ﬁ2\‘\»l§∑\—\‡=Ç\≈i\0ˇ\0Å\»ﬂëÆª-Ç>UÇé[¶π™Keÿ§én;\Í\‚\ÁX\“4˝\›>≈Ø˛˙ë\‘S¸?\·ùCK\’\'ª\‘|M©k\€\”dP\‹$P\≈æ#Qì[\Ù\ı\Õd\Ê\Ÿc®\Á÷äO∆≥\0¸iP\”jEZ\0z\”˘\ı¶fë\ÿ\–Êäèq\Ù4Pìs\ÎK2(\ÔIœ≠-ü\Õsx˘ó≠ûS\‡\\Xh3h∫Bù__õY\‘\Ã\ÚI\Ú[\ƒ.ükH\ÁÓçº\0k\–<9£^\Èq∑\€uõù^\Úoûb\ÿXëΩ#^†}k\À¸\‡˝wA\–S\≈\ﬁº˙≠\Õ\≈\Êß\·˚¸y\…\Á∏ˇ\0\À7\0©\È\Ò∆ë\‚\…$[xu¯˙\—u≤\Ú\‘ˇ\0u\‚=GΩv÷ßøwTc\ ¯çm\‚F\”M*˚G\Zú&}6[•S\r\‚Ö\›\Ú∫\Ø!sús]\◊\÷\÷\˜Vê\À4q\Õr\≈ ç\‹ïÄ$Ö\ƒ@\Ò\ÿWî¯£¬≤\ËZ|>\—<ZV\’.m3C∏µé\Ê{I<\Õ\Í!ëJ∫ =	ÉW\ﬂ\√[¸lº∫û≥yØNöv£<\rp©\Zâìb~\ÌT\ı\⁄\Ó~Äû\‘\ÂF∫bR}èF}N\Œ=J9\Ô ]Begä—§Q+®%S9 \0I¿ß¨â!`¨¨W∞sååå˝@\'\Ø)\Ò2¡§¸Yæ∏Ω\—o5+\…\‰\”n4{´;vô†Tó\Ì\\\Ì\‡éZì·ÆπmoØ|Q\Ò±#\È.≠\r§ñ∑≤l{h¢á\‰zæ\„åu\≈G\’›Øp\Ê=5o≠\⁄˘\ÏV\Í®G∏{P\„\ÕX\ÀmS®Rx\Œ1û+è\Ò§-~0x}•\'…µ\˛°<qû≠+\œm\0w$1¿Æ]≥6VÉ‚´§∫~ßg}Ü	˙4ç≥B\‡\Ùb_\Ã\È÷¥µY\Ògä4?hñ\ˆñ∑V\ˆVö°t˚d*Érq\˜p\Ò´(=A»≠aEA\Û7†s\\\Ô4ª--\n\Õˇ\03M>ﬁûc\0º≠Q\Ò6±q\·˝,\Í˙d˙™G4\"X-O\Œ!f√∫Å\ÀáZ\‚\Ó_\å4_Î∫≠÷∑§\ﬂY\‹\È⁄öX¿\∆\”MíH\\F\‚º\›\”<V\Õ\Ôé\ÓuYÉ¥©\ı\ÕHå§ìF\÷\÷\ =\ZWª\¨%E≠or‘Æ¨vJA€±\Àn\Èë÷üLcπ\ƒEïs;Ç˝ß\◊1v5O[\’\‡\\Óá™‹£\…Ñw2®\…1\∆7=\Œ\rZÆ\‚G\Õ\\ﬂ\≈\‡˝\ﬂ\Ï{≥ü˚bˇ\0\‚*\‚ìi0oKúŒùo¶\‹|B\–-¥HD\”X\Õ?àµ=Aø÷Åu!$\Ù\  ßi\Ë5\ﬁ\ﬂ]UÑ-<Ñ§pù\Ìêü@	\Ù\ÕqöÁÉº*∫\r¶©´h&•%Ω§mû\ËÓ¶∏xí8\—];\œ”äè\·\Ï⁄Æó\‚\ﬂxkVøm^[[ò.§êºñ\È+:µ´±\·ä\ÏF\‹:Çz\Ï´i«ôt9†\ı∞\Î\Õ=¥øç^ªidñ\ÎR\—5KI\ﬂ8S\Â5¥®ˇ\0¿è>\’\›n\∆Fzˇ\0?\?ëØ<¯ãØ\\hø>¶üa˝ß®Mg´Gojú+;ãt\‹«∞[üc\ÈVtmƒû\‘5]/≈ñ\˜Z¥>r\›i˙Æçc$∞yL†\nF	Bé≠◊®a\ÎR\È9\∆-ïùé\Ï|‹éG_À≠(˘∫s^9y\„\›VOå∞y£X\”4\r:\◊t:W\ÿ\›\'\’gëy ëê£øWA§\Î^9m/Q\”u»∫¸\˜Wo¢\“\¬l-°ë\˜Bgs◊èzóÜí›£Ntz/BA\Í:\”T\‡üj\·\Ïuoà7ZÖ<7ai™¡g∞\›^jH\—\À2¶\“UUrny©º\‚çq\Ù]\"\rK\√:\’∆π¨k{q5¨v\5\∆ﬂò´6⁄èb˚ï\Œv{Ü\Ê\Âq∏zg¶#IÉ∏år:ä\Úáæ\Ò_Ç|E\‚V\Ó\ \€V’µãÇdømTàL[ù\‘+∏\n\‹\æü\„õ{\›*\ı\Ï’ç\Â\≈\ \Îí\\˘\Ë´$õÇCn6\Ì\nº\’JÖæ–π¸é\Ô=ª\”\…€å\Òëë\\nâc\„\Õ+OÉOªº\–\ıo/r\rb\ÊYVWS–º*ò${VóÑb\Òú7\ˆ\ﬁ#ñ\÷\ˆ\‚+ñ{[\Î!µ\'Ö˘Ud<©S˘V2á/PN\Ê˛\ÛKLß\Ê≥(}=j<\”˘\ı†\Êπ?å?l_Ñ>5}2W∂\‘ “Æ&ÇU\Œ\Âd≥]MK\ˆK}B9\Ì/vµï\ƒO¿nõll˚i\«p+È∫¢j\⁄]ç\ÚÆ\Ú\÷+¥\Ù\”u\\Ø=¯1¨[ˇ\0¬©\ïΩ∆•m%\ıµö[JØ2\Ó˘$x\◊#=¬É¯◊†,ã\'›ë[\ËsD¢\‡˘X‘Æâ;Åﬁ£Ç\‚+®xdIaì%$çÉ+`êpG^APk\«cQõ¿^#]\Z\Ò\Ï5U±ë\Ì\Ó#¡\"d\Á\0{ö\ÚOÑ>2ªæ¯7£¯W¿\À\ˆˇ\0\⁄Arì\ﬁ\\É\ˆ]<âLm+ûÆ¿\‰.rGJ\⁄yTá2dπ§\Ï\œtä\‚\‘\÷\…fçÆ∂	|Ä\„~\¬H\r∑Æ2œ®5W√û&\“<Yßˇ\0hËöçæ£g\Êò|\Îbn\0q\ﬂº{èZ\Ú8|X/<T˛-ä\Œ˙\·u¶Ö}\r¨cÃ≤øYYù%^™>cÜ\‚´˛\…1\ﬂ\⁄¯w\≈\ˆ\ZçºVV∫çºin\0GkE\«˚\€2}\Í˛Ø\Ó∑}Q\\⁄ûø°\ÎW\◊>.\ÒVóy\ÿl\ﬁ\“\ÔN∏Q\√\€M\ˆÉ\√&}3]†\ı¸+ì\•\›\Ã\ﬂ<{\“4\\€ˇ\0d˝üêj÷¨JèQºK˘\”~\ÎöΩØä\·\‘n\Zi4\œ\ﬂZyíà\‡åô=Ü\“\√\5É¶˙ïé¿FG\"π?åEó\·Gà\·`Bﬁ•Ωâ\'˛y\\\\¡	¸6ΩY\á\ƒ\∆jw\÷7M%¶ó4´u∏a\ﬁÜD™Ω\—\«F\Ë{Wô.ü\‚MK\¬w∑\◊⁄¨˙ê\ÒVÄæ$˚å¥∏Ç\Ó\ﬁ\Âcãí\·\ﬁB;WVã\ÊN]jMt=7·ç§ögÄ¥].iìih˙[6zõiZ˙\'\È]OAì¿\Œ?ëè\Ã ±|!4\ZÖÖ\ı’´,ñ∑ö÷©sëù\ —Ω\Ù\Ï#Çe ˙{◊èüx\œZ¯Ö´x£OπHº	§¯é?¿â¿ô-\ÂìrY›á\–˙Ré÷©%Ös(%s\ﬂ:s€ß˘¸\ÍD\Îé¯\Œ+\Œ<A\ÒáG\—˛&Xxx\Í6iQ\Ÿ\›>•®M)+ ≤{o3\Ó\Ô¿9\Õv~\Ò&ó\„Kµ\Ë\˜±j∂øií\Ÿf∑˘ï\‰SÇ<\Z\Áï9¡]¢π¢\ˆ5c\È˛\œcOÆS¿:Ü©≠C\‚=B˙\·g¥õ\\ªãK1Ø\ l£dâ[?\Ô$á?\ÌWVÜ≤4\ˆ®t¯%∫ª8¥∂äKâ\€8\¬\"óc\Ù¿\'\5\Âˇ\0ˇ\0∂\ÙOD5˚ô\'ü\∆VRxâa|\‚\Œ\„p\Û-¿\Ï9SèU™?Ø¸g~-|\·ˇ\0∞X[x≤x4x&¡kôP\Óí˘˝¢é4!ˇ\0\ﬂµ\∆\⁄Gâa\ÒwÄn\€\≈PK3jì\ÿ	î™\"I≠ff#\Á\Á˛=\∆zt\ËØgv÷ß4•≠ë\Íë\Âõh\ÂΩ;ˇ\0û\ry¶óas\„\⁄\Û\ƒ&\Áfó\·nt!åì∫p\"Y]ªei\0ˇ\0uΩ\rkÎñ∫«á|+Æ\Î∑\ﬁ3øó˚/MπΩH\Ì\Ì`àHù¿$´qìW˛¯U|\‡G%§∫ä\÷9\ıå˛\Ú\‚\ÍE\›3±=\˜±\«“ππc\ZnW.˙ùM\≈\ƒV∂\”\\O*Co\n\ÔñY*\"é2\ƒ\÷í\¬\Ó\rB\’.mfé\Ê\›˛\Ï–∞to°\Z\‡˛\'\Àcu\‚/á˙n∑*/ágªªû\Òn\\\œH-°rqÖ\‹X\‡˝\Ï\Z\Ìt}&\”K∑d∞¥KhY∑\ÏÖ@Fc\‘f\·h¶>mMß-A4\Ò\€\ÀR»±I!\¬#∞è∞=jj\…\ËQ\œM¶¯ªQ\◊\Ô$\Zﬁù°Ëë∂\ÀT≤≥˚MÎØ´<òPkç¯\‡\‘\”uok≥jzû©®ÀØ\Í\Zyk©\˜#G\€r¯Mu>\"\œàµmb[ª]\È∂\"5X\Ù\» ç\ÔS9V“©¯O\·Nô\·ù\ﬁ\ \‚ˇ\0T‘ÆIsw!\‘eé9\Êï\˜ªlB_z\ÌSá≤iΩLµ\Ê6\ıøà\Z\'á¸Ge°jw\–\ÿ\›\ﬁYµ\Úô\‰X\”j≤F1?x\Âò§{W\‚èk3|m\Áá¥≠V\ \œ\√V6j:ﬂó\Z\»\Ú\Á\ÓAá\·pΩNEY‘æ\Ë˛#¯ùΩ´iñ≥\Ëzfé∂:~ö[\"Kô$wñ\‚Súú\0\\¯C°j±\“4{x|0∂ó\Òjug\0i\√+ríOøpxx•\’ÿó\Œ\ÃMS«ó∫\ƒMR{/^jwØ¢\‹GxÅB@∑Ø\Ê¨J˝$H\ƒ\·/vΩ`ˇ\0l¯∑R¯stö\ˆπÓ≥ØM`-tΩèµCh≤¨óR?ïíÄ†+ì\∆xØióNâµÒ©íæbZ=≠º{xC,Å\Êc˝\‚¡c\\ZM\'I\”\Ù_;\Ï\ZuÆúe˚\Ìm\Z°pz\‰Æ1\Ù¨qT¢ï°±>\Œ]\œ/¯Y\„\ÌO\–<;£]\›E•\€xtM,\Ê\ËyO\√JêEmÜì\‰|ú\ÕU¯C.≥\‡˚o_\€x7\\∫\◊u\ÌVk´C}\n¡∂.Z!+6xfêú\„\ÔW≥EQ\»\Ú,QôYæ\Û ?“ß\Ûò\·à`/`æïú±Q\˜πc\Ò\Ï›í\ÏyGÖ¸\Ò¡˛\“</•ç\Œk;¶∫ø\÷\rÈëÆ\˜\Ã“ºhÜ,®b\≈rz\n\Ô|#·ô¥k≠oX\‘&ä\Î_◊Æñ\Ê\˜\Ï\„Aq˘p¡Ó™ã\ŒGS[¥\ıÆY\’\Á\Ëi$KN\Á÷ô∏z\“+\Z¿≤L∂ﬁ¥s\ÎI¯\“\Û\ÎJ¿*\“QKLi^á46\Ê˚¿ü∆ùO©\Z0i\ÙS∏\Á÷ë~F\‚ùF\”\ÈL\n∂∂6\ˆ\'\Ÿ`\Êi\Âl‰ºç’çOO\⁄}(\⁄})\Û	h2üK≤ñê\∆s\ÎMßµ&\r\0µ?4˙ÜÄë\ÎP9;∫\”‹èZÖ\ÿ\–ôj*\◊\Ÿ\≈V\«ˇ\0\Zä0a\’[änh\ÕIf_át3\·\›>K∫3\⁄âd∂åÆ<ò§vs}ã\Z]g\¬˙à§Ü]WF±\’.\"˚í\›Bå\„˛é\Z—¢ü3[2yJV:ó£\Á˚?K±∞\œ_≤[$y˙\ÕsA\”¸EoZï±ù†ê\…\—K$RDv\Ì%dFw¥(©ª‹¢éì¢\ÿ\Ë6\Ê+|¶\ıíI#J\Ì\ıë\ÚﬂïCu\·}P\’∆≠u§\Ÿ]j{U\r‹±nêÖ\·NOSé\‰V¶\—\ÎEW<∑∏Yæ0ù∑é¥\Ï{˚â≠\Ï\Z\ÊßXzÃë∫øóÏ§®≠Ÿ§8`°T$U^ä£\ÿ\neúõV\0FhY∂í§˙1˘æ∏ßI# ªZW#˚¨r?ï7ØJ(\‘S≥M\Õ†f™j∫l\Z÷è¶\‹\˜\÷\“Z\Õ\«;Yv\ÒVsIº\”¥±ë¨xN\À\ƒ^èH‘ûY¢ça+sys,ël(\‡é˘\ÕI\·\ﬂiæ”çñõbC∫y\ÓÕñf\ıvn†vµ(¶\Ê\⁄Â∏πU\Ó1£I$I^(\ﬁhA\»\…\Û™∑Pß∂{\— åJ˙S\Ë•\ÕmáaiΩã∑wØ–ëë@\‰aâ+\ÈIN•ØQ\Ë7\Ê^ú”õ\Ê]¨\ŒG÷ä( g>¥QKE«†ú˙\—œ≠QpAEP!\ı\'\„QÊùö\0}T÷¥[/i\ÈzåFkeâ\ﬁ=\‰o\Ú\‰G#êüj∑E5£∏˛á\\˜\√\⁄>öñCD\”\'çfôï‰∞å∞Y&wü\ÓÇ\0≠Ω?K\”\ÙΩ\ﬂ`”¨\Ï7\ı˚4=ﬂê´\Ï\’9\ N\ÏÅ#N>\·\⁄Gπ¨\›/C≤\”o/\Ôm¨‚≥öˇ\0\À≠∫\ÏW)ø∫÷ñh\ÕM\Ù≤/sô\Ò\'Å¥z\Áª\”a7õYûxwF“∑∏gﬁ¨i>–Ø4)LÇ!j#{r\—2{eq∏˚ö\÷\‘[9\ÿrv‘∫j$6»ë\ä(\Ù©\Êï\Ìr≠•ÉO\–\Ì\Ù\ÌkW\’`v\Û\ı(≠`ïOa ®\√\ﬂ\Á\Ê©\ﬂ¸?\Ê©´I©\ﬁ\Èûu‹åe ±\ ¡v\Óë∂±=\Ò[ISU)5≥2zô∫ßÖ\Ù}}∑j:d-∑ae˝\”€∑i\€¡âß|5]7MM*\Î±\È°é;!,[í3¥ybbª∂\·Eu\…KV™\Œ*…ë à¥ù.\”\√˙uéõ¶\€%ïçúi1«ìµúgπ\'©Ø.∏˝ù\Ï\Ô|W®\‹œ¨\›/á/µG\÷nt∏$ëZ\‚fm\·Y∑`\0¸\‰WÆQNùi\”m\≈\Ó9EJ\◊)\ÿ\Ë\⁄nõeüg•\Ÿ\€i\Òpñ©\0\Ú\◊NrO©5\ÕY¸7õM]^\”L\Ò-\ˆì¢\Í7\◊\Zå∂6\—$Å\Ám\“*JNW?•v|˙“ÆG^8\Õ/m>Æ\· à¥\›6\◊G\”m4˚t∂≤µçb∑Ö	\Ÿ\Z™\‡ûs\Û\…\ÍE[¸i)3Y\\¢¨∫=Ö∆µß\Í\Ú\€,öñü∞Z\‹6víç≤`zï\„5π§I≠j^|¢Z\Èzë‘§\…˘ôñ\÷x£\€2íkS\Ò¢ü3∫a†\›CO∂\÷4€Ω>\ˆ-\ˆópΩº\ Te\⁄Eci:à¥’Ç\’¸Ckqca\"ù¥ˇ\0\Ù†£’∑\‡ö\Ë3O‰åÉëT§“≤∑ õK≥\‘4ˇ\0±\Í\Òj6§fHØ#Y\€˚\€z\Ù5å\ﬂ\r|+#Gç#\…\€¸6\˜2\ƒ?\Ò\«\–n\‡úg\\ıß«ñ]√ï=jJRZ&MäZ?Ütçè∞\È\—[…ù\∆Cô$?I±≥¯\‘+\Úéx\ÁçK\ﬂˇ\0…®lhw>¥m§\œ\0\ÁÉ“ó6;˙Q£e>¥s\ÎG>¥S\ﬁó$ç≠\≈>a#I+Ä™Õ∏c≠i\‘\0\Ù©j4©3O@∏˙_∆õöÄO¶s\ÎO\Õ\0>ùœ≠2ù¯\–\”“ò§7Cü•89 ë\»∂J*?3\Â\›\€÷§\⁄y8\Ëp~ßµK`Rgxßz\Û\ﬂóZ\0MîSá\Õ\–\Áú~>î*•è\0u8≠\r¢õs}ógu}>V∞Ip˘<D\›œ•sû∫\÷\Ô¸ß^xÅî\Í\˜Ä\œ\" ¿@\Ì\¬˝EW+∑0∫ù&iπ©v\‘lïò\»\È\ÈK\Â\“fö\‘f¢ß\‘∆™¿#ökQEH∑ü\Ô~¥U∆ä∞<éå\”7\Z3PX¸—ëúw¶S&ºé\∆\ŒkâX§QD\Û\»TdÑ^ß\È@v\œoZ=}π>\’\rç\Ï\Zïùù\Ì¨Ü[{\»Rx$Aå\∆\ÎΩN>á?J\Â≠˛!≠\◊ƒ¥\\ƒZ{Ke\ÂŒíjá!\Ú4\Û\0\Ù8ãì\Ëh\‰zä\Á_I∏u\œG^\‘$—º?©\ﬁ¡∏ñ\Œ\“y„Öé7îM¡~º+;OÒµåæ≤\Òu\ÎgXK¶≈©Ã∏\ﬂ\‰!è{èA\…\Ùím\\wF¯`z\‘\ZÜ°k§Z=\’\ı\Ã6V©Ä\”\\H#E\œL±\‡f§ÜhÆ\·Üky<˚Y\‚Y\—¿‡´ååBG≠x◊è’æ;x∑W\ï{ü¶xv\–\›\ÍW\ÛEπM\€±DûQv∂Ol\ÙÆöi\Ú\ﬂN§N\\™Á¥ò\ˆ*8?+Ä\ ›à=\ˆ84u\Ì^\!ßè\‡ˇ\0Ü£∏ªñ\ı\÷)#[á?4±	\‹F¸\ı êA\Ù\Ê±>7|`õ¿\Ú[¯gCgä\ıAég%úræ\Ò›∞p\√Œ•WJâ\‘Qè3=d¸Ωx§\‹={f∏ØÇ\˜∫\≈\«\√=%ºAvo\ı•û\‘\ˆ®ñL$òà\‰\ı\’j⁄•¶á•\›\Í7\Ûk+8L\”\Õ\‹.p?2qX88Àïñûó-\‰z\˜\≈ç\‡\›z\ÛƒöøΩ\—\Ó4Vi\›\"µªp\Ã\ÒØ‹ëΩ	\Ù≠™ÜözÖ\«få\”(§G`{îôÄípø•bY¯\”A\‘|C6âo´ZK´\∆ç¥n≠!\⁄2 ∏<ê9>ÇÑõ\Ë;£nä]¨XÉµ±Éésè\‰*O_lÌûî=\ÿfå\”i3\∆{c4âA\‹\Ú?,\”\ÎFæá\«P)ºIº\—\Âï-6˝Ààn\"R\‰ˇ\0¥∑@cæ\”Zªøû?JpJ>nG#¸i9\ı¨\r\≈\Í>\ÒØádÖcáCÉMû	\ÛÃøjäG`Gl´Qrª]\0ﬂ¢ì\Ò£∂s«Ø\„è\ÁR1i\Ù\Ã“≠&¸hJJw>¥\0˙(\Õ*©v\n†±<\0()vüJU` ¨§aê√°¡ ˛†è¿\”ˇ\0\ZëI‹©|ß\ÏrsR\È µî,G.õ\Ë∏O2&S“†\¸¢m\ RNB>\€N\ﬂ\ÈQª+[\\\‘Jû¢E?7td˚Tµfb•-\"R\–π\È\Ó@èJw\„Xñ>.\”oºa¨¯b\'a´iV\÷\˜7\√\Âh\Áê©\Ôå\Z\⁄\Ìûﬁµ.\Ë\Ó}k:Oi±¯§xp\ﬁ\ƒu÷≥:â≤˛5áp√ì\€ ÉèB+R\Õ|€àPsπ\Ò^9\·\ﬁ!\Ò/Ñ|j\ÍWQ\Òà\ıáYà\‰i\ÀgvêCè\ÓÅnç\ı#÷∂Ö>d\ﬂb%+;\…\Ûmi\∆qúRfº\√\∆:\ı\Á¸4G\√\€\\HñIa{$\ﬂo(ãw\–\€9¸k\”}Oa¡¸*gNPµ˙´ñü2–ô)\…\ﬂ\ÿd˛x˛`älu\ƒ¸J\ÒÂèà>h\ˆí¥-´x¶rc`≠-\‚yf_ß#4°wd.áuö\¬¯Ö\‚è¯/P÷≠†Ü\‚\‚\ﬁ[U\Ÿ6qâ.cà˛è[,Í™¨Xf\⁄û	\Ù˙\*\√¯â\·\…|g\ˇ\0[\—-e\›\ﬁ[f\ﬁF<y\»\Î\"~Q˘\”\Â≥\◊`∏ó\ﬁ\"\‘-~1G\·A?\ŸR\ËO©,˚Oõ\Á%»âó=1Ü_\Ãz’Øx\÷\√\√˛\’\ı\‚TáM≥4V[Yg\ﬁ\"\Ú:˝\ÌÃ´éπ`:ö≠sc{\Ò¬æ!í\œkc^Z_bA˛ç#¥®ø2∞˙É\ÈYw\r\Óˇ\0\· ∏í\ÀVÜ\€\√\◊\⁄\Ìøà\Ôm\◊\‚)Sm\—Qû5\'>¢∂å`\‰õd›ë\Ëø4ΩKY∏\—f\—\ım3S≥ªèN\‘#ö\’Z+;á;R7ï~R[∑<\ˆ´\Óç◊äæ*_=\…k(<B-ñY\ﬂ	\n\√i\n\»9\·F\ˆ?ç]oÖ:©\Ò?Ωµö\Í\‚\ﬁ\Í\Í\∆Çñó6\‰öH\«èL\÷Ä¸/•¯\√\·®mV6π≥\’|A©kwëπEõu\‰˛\\r\…9\ˆ∑ö°f\‡J\Ê:C\Ò\"\œQëS\√\⁄v£\‚fêg\Ìv1¥˛ªæ\‘¿÷æç¨\ﬁ\‹J5\r\◊H¥\Âv^ãâ^Op™∆Ø*Ç™´∂4AµcçB ¸=zg∑J\„n6µã˘ì~4¥≈ß~5fùöäûÜÄ$¸i\Znßb#É˙‘ë\√&\“\€jåìé\0§ØmÖ†π£4\“b¡\„\Î“íò\…\Û\ÔKöã4\Ï\–—™ZÖ)\ ∆Ä3|A\„Ox>\ﬂ\ÌZ˛πe§\¬Õ∞	ß\ﬁ\ÓﬁäΩI\ˆ\‚\\Ÿ\÷\”3Ac\‡-kS\‘%i\Z\∆\⁄\ﬁ\‚<4K\˜ùø\Ÿ\œA^±k\ß¡7f\Ó\È\"\Ë\»\“yí\€˘§∑®\ÿ\Áﬂ¥≈ºæ\wä|Q•\ÎS\⁄k\⁄Œô˝áod∞\∆?s¥y˚\r»ü2\Â±\∆\·\Î^\Œ\ni\…Sî[ì9j∫ë\÷\‚x7\‚g\≈_x&\\\Ëû—º?\‰˝≤;¸˚çJ˙\›FUê\„\n|\Ò]å|i≠hFm·é£\r‘∂¯∂õZ∫∑Ç8ú\Ùfã;∏™˛∂\’~7Å¸%®jqﬂ≠∆öR\÷Å\Ì˛\œ\Z\0>^™H8Æõ\∆_<7\\⁄\÷\Í˚[\‘\Ì\⁄\Ó\ﬁ¥E•\« {π\Œ2™®Wp\Í\ƒ`Síä´»©\‹q\÷7π\Áø|y\„Ω\‚Gã¸3\‚€´	ááaÑI\ˆXT;\\\…\€rú`bΩ_ƒû$¥\á\Ô5ãÿ§∏KPã≠®&[âò\Ìé(˝ÿê=\Õ|\Û˚8¸L{\œ	\Íw\⁄GÇ5ˇ\0¯ó\\øóU\÷o≠°é\ﬂOY]úGs\Ã\·X( \‡+\÷|Qßx∑\∆\⁄<6o•\È∫\√q\Ó.µ¥ª¥NÆ#Q\ZQë‘öåM´Í¨Ç|ö>.\◊~(-å:Ωî∂ZMï\»E˛\Ã6µ’£n\n±;9!ÅboSäg\¬˝\ƒ>/µ\‘\Ôº_\‚_GÆ\ÿ\ﬂ=ëé\÷\‚+kd\€\›#ç@¸\Î∞]/ƒæ(ku\Òi˙>ó\ƒW-c¶\œ%\Ã\˜ç‹ã$§(D†\·y9´K\·{˚\r_Tª\“5®\Ù\Ù\‘M$w\"píL:\„>\Ù\›h{?fíLüf\Ôsí\Òu∆ØÖ´xR\ˆ\˜\Ì\◊Zå\ˆñVW*<∂ñ	\…gf¶˚^°B%X\‘aPU\Ù\≈yΩüÑV\À\‚fô˛õy™\ﬁZ\⁄…´jZ•„Üû\Ê\‚f\Ú¢UQ\»≥W£\¬YF3Â∑ØZ\‰\ƒI.X\ƒ\÷\‹M[R≥\–m\“}N˙\ﬂNÖ\∆VKπV%l\Ù¡b3XS¸J\\ﬁ\ﬂ\Ù}D\Í\ˆ∑í\Îˇ\0@´hˇ\0\Ù=&sy5®\÷\ı©[Ã∏\÷us\ˆãôò\ı π!†\≈uB\Êe˚≤2˝\ﬂ\‰+û\Ù\Õu9\À/\⁄_\ﬁAiï¨Üë∂´œ•MH?\⁄f\\∆∫\nD•¨\€]\≈f5\rKœ≠ETµ\0¢ä)Xn?ﬁ¢§\€˛\Ì@y\Í3Qyû\Ù¸\÷eãæºü\ˆê\Òe÷ì\‡x¥kö\ÕrI°y|\À\nF*˚± c\‹W™f∞ºA\‡\›+\≈\ZŒÅ™jH\ÛË≤º\÷ å6ñmπQ\Úäﬁå\„N¢îëN\÷Fo¬ΩKP\“\Ù\Ë<Ø∫/âº=nêÜQÖº±TQ\È\Î¥e[:\ZÇ\ﬂG{/h\ˆ!\‚y¢\’\ı]l4l≈æ\À<	=ô Qû™á+°\◊|3•¯†\€ˇ\0j@eπµb\ˆ\◊qJ\ÒOn«ù\— º©\œnEK°xwO\\ÙsH\Êí\Ê\„hΩªù\Ó\'òWv$`) ¢mµ‘ûVh\Í\rk•j2àû\·í\÷W1Gèü\˜næIØ\ráT\Ò~\…jSF≤ä¿¯L[\»\Ûj\Êº>N\¬\ÈL)+\œ=πØxÅáò7èì?0ˇ\0d\ı\»\⁄¯§¯NæΩ∏\€Em)\Óc\‰≥b∞¸*\Ë‘ç5i+Ñ¢Œã\√\ˆM†h:\rÉ\ n>¡emlfaÇ˚#E\…Ö|ﬂ´hz\œ√øä\ﬁ4\“\⁄\œY\ÒÖu[Ho\ı3\·\ÿT\ﬁy\'öDIA|üò≤í?∫}+\ÈãU*\ÿ]<~z\√\Z\À$*@,\Ê {◊õ\Ÿ¯W\«W˛0Ω÷¶‘¨<8n\Ù°§M%´õôi4í£Dú*úJG\Õ]8Z™NOr*&\Ù:\r\‚gÅ\ıM*\÷M\ƒZL6^Rmöao$*ø\¬Qà ◊É|nãOΩ˝§4◊æ¥‘Øº:,-e\’IFíhñ5g.°A;@e$\Ù\0èZ˙+I\éã\·˝.\«N≤\”-≈•ú+-4k+úu,ORkáæ¯C}≠¸`\Ò7à\Ô\ıKà|=®X¡m\rùïŸç\Â˝\‘I$rq¬úG°´\¬÷•J§ß}»©%k&ï\Ò/¿q\È÷©¶xÉK¥\”\÷5Ñì\…\næø1\ÈX\ﬁ\"◊¥x\Á¡>≥\’-u\r:y.5õÿ¨\ÁYD¢\ŸT§,Tüïà\Œ\rz\rΩ•ºqZ\«kVë(	FªP‹åö\«\ÒGÇ\Ù\ﬂZÿ£¥˙e\ˆü?\⁄lu-1ÑS\⁄\ Wi*q û\ÍkëNöï\ı5≥µéÖ\‰id,Hë\€˚£˙\nP¨y<g\Æaº/¨J´«ç5gè˚∞Z\⁄\∆1]\—¸/ßhSKqlìO{0Uö\Ú\ÚwöW˙≥\Á\Ù\Ã÷ªñlQG>¥üç@/\∆/\Z\\xK\¬1C¶ ±\Î:\Ì\‹:MórÜW\⁄\“˛\Œ5K\„5Æó\‡Ü\⁄Ze≠Ωµ◊Ü\Ô\Ï\Á\—8√¥\À2(Rz∑ôm\ {\ÈZö\ÔÄe\Ò\≈MƒóìC&ì£ZáÜ\”so7~c∞oLä\’\ÒWÑ4ˇ\0≈§G©âºù7PáRHcl,\“Gø\n˘\Ì\ÕwSî)\⁄\ﬂ37\ŒM\–o<+\ÒsGjóW◊æ \“o\€WI¶fçgÇX3\Zè∫\Ã\Î\Ó©</u¢¸R\ÒE\≈\„\"Æ©®AæG˝›¥V1\Ï¿\Áì[\◊\Z\◊?¥\Ò#\‹f(4õãm\ﬂtìD·áπ	É\\áé>\ﬁk\⁄ç¨4\ﬁiñæ%iØf”º¥*\˜M\÷>oUWnH°\Œ\‹Z°æ0\Ònπ\·\Ÿ\€H\ÒC_$>!ãK\“o.Y¢\\]\… à\…;d¸è•j\›\ﬁ¯ß¡~/\\È\Òµiw£j\“\œguv\ÎZu–Ñ\Õ	ç˛\ÒC\‰∫\‰\˜jµ\„œá\¸D\Œï¢\Íèekkykw4v´∏J±.\—=M\„/\ﬁ¯∑\≈\ﬁiEø¸#Zmƒö≠\ ˚\…/ Ls6~Üú%Oñ\√\‘nï\‚\Î\Î\Ô\ZG¶_h\'L¥æ\”gπ\“uá˝\ı»éXº¯\‰N®pc|z.zW	\„?à~1\_\«&µHõX\T˙}îmß⁄™C%ª‹øëí{˘\‡˛U\Ëzµª\›|D\ÑÄé\ÀO\’fôÄ\»Q Å3ÿ∞V¿\ÔÉ\È\\5Âéø\‚oç∫¨¯~\Í\”√ûnë+\Î6\„\”Ã≥@z\ÔûU<uZQ\ˆ\\\◊{X\Œw\Ëv¸S™x™\ﬂ\ƒ\Ú\Íö\\Z)\”u€ç\"P˛c™¬ë≥a\˜è\œ⁄∏\›_\‘\Ó?hÔàã£i\Z¡§X\ﬁ\‹OrbKq\rÄ\‡π\ﬂ¿\Ík∞_	\Í\⁄Oà5´˝[∂∂≤÷Æ\Õ˝›éßhf‹ïUi£*\„∂å©Æ+\·3kˇ\0Ñ¿\Íöf•ÆùS^∫∏˛ÿ±∑G{ÜF\Ú\ˆº}U@Q∑>ºQ\¬\”k®\Ó’ÆzèàºEc\·=R\÷59\⁄-6\¬#4\“\"\ÂèÕ¥\0=\…\«◊ä\„\ÙüxãN’†õ\≈\i˙Vô¨M\rñógnÆ\◊V\Û\ Hä)bP\ÿ˚§\’\œ\È:óè|.∫}ùê\“Dwvó\Ë⁄æ“≤\…o*:\ƒËÖé\∆\«5KR¥\Ò≠\Ò¿¯Ö\Ù®m\ı˝\“\ÿ\È€ú5\ƒvNcvë˛bA,¿CXSÑ9]\˜*\Ï\Ù\Zu6ûµ\∆jKN\Á÷õN¸h\0´\⁄L\Îm™ZM\"É∂E\‹;U\Z\À\Ò/ä\Ùˇ\0Ccu©%\Û\√q7ó\ÊX\⁄=«î?º\·A¿\˜5Q\\\Œ\»/\ˆsi!¯Sk¶\œ,ìM¶jöûú\“\Ã˚\ﬁMóì*ú˚Wß#xØ\'¯K\Ò\√\÷˛\r)=\’\ƒ2\‹jzï\·I-\'\∆\Ÿo%e\Áo]§°Ω;M’≠\ıH\ﬁ[IdtV\⁄\ZH\ﬁ3è°•x®\Õÿò\ÀMK)u@_S“º\œZ¯ùÆ\Ë˛\0\Ò>≠ß¯SÖ¥H\Ógjç∫6‹≤\"ú≤Å\…#ås^è0;:W\Ò#\«>ˇ\0Ög\„k&\Òï$\Ûh:Ö∫\€\≈té\Ì+[:™Ö%ã‘ìä(\≈JI5pì\–\Î¸=©\Í\ZúJ\◊\⁄\r∆éVó|\”C$eà\Œ°\‹z\Ÿ\Û1å\˜\È\\\ˆè\„jñ∫tvöﬁùs+¡Té\ÂÑà\–S9\Í\rgj\„\œç<E§_H\˜§Ziri\Zmå{Æn%ú\\¨®∏\‰è\›\ƒ\∆F¿P\ÍOQMQîõIl\»\Ï˝Oa÷§\ı\ˆ8?\\\„\≈¯O\‚∆ü\œã\„ã¡\⁄Õå\Ï%±\‘\'.Æùö\È >´ö\«¯WÆ¯ö\nxÉGΩëo¸EßX\«}¶^j\À70›§\Ôi\Á)˚å\n|\Ÿ\ÈU\Ï%g\'•Éô\\\“\ö\«\'\∆/â◊ûO\Ôí-\Õ[ï¨\‰≈á\Ê+™ˇ\0ÑèGè\≈\√Õ©Z.ºcYFûdrå2ºg9 Ç=AÆ¿æ\Ò \ÒŒ£/ã\Õ.µ¥Æt∏\ˆ\\¨\Ì¿mπ\»\‰∞«®>ïNo¯ãC]K†\⁄¯≥R\’.§‘¥\Õ^9\"Ç\‚<≠±ÇI\ﬁBm@9\Õt Ö9M˚›åπ§∫∞∑¿Z\›\œm$rx¶£`Gòãúq\‹x\ˆÆ\·\Ï\÷\”¡\\”MÅA]\'¡pj2≤\Ú∑QCg˝\‚\Î\Û>\ıâ\c\≈^\¬ø\Ë¨˙Ñ∑\Ò@\“_Ÿ¶ùs5\√\›J¡•\»€ªòè†©>\Èæ)\Nó©ãø\‹\ÍW∑r ≤ôµh\ÃZ|*V\ \⁄@[\‰h\◊y`Ω\€ﬁät\‘a5q9]¶;F\”n\ı\œ⁄´\∆:îò\ZátK+4\œ_:\Êì\Èú~íﬁΩ≈æ*∂\gá\Â\’&äKÀÜñ+;+y\◊w2∆ê\«\Ô\˜\ÿ\˜¬ì\ÿ\◊\r§\√}\\◊\ƒZñ≥Æ3_\≈\‚±∫Ω›Ñ,\Y^F_\ÀP£ëâë7t˘qZû6ö\”_á√öŒã¨i◊öèá\ı\’ ±7Ö”àö?,Ñ\À\‰n,8\ÎJ¥UJêW\—\"¢˘bu>\Ò>*\÷ï´\€\ƒa[\Ë<\œ!\ŒJæ\∆\»\Î\√ß–åuÆS«ñ2\ﬁ|x¯9\0V}j˚hHµ\⁄\rax/\√>&\_ãØ5\›g\√r^õΩ:;+84;\ÿ\Â\Zrµƒ∑#*{ £p\Ë≤\ıÀÆ|z\◊à¸Ig4Vz£\ﬁZ\⁄\È_≥º*ñõº\«\Ú˛PY∏€ûµ¨(¬ùI>m,Cìí\—Ø\‚o\ÿx\√Q“ß’†k´M>;Ç∂˛cF<\Ÿ6!#Æ–í`{\’J˘æxP\’\Óoß\‘¸7fô¥e\Ô-\˜2áHÄç\Õf\›h∂\⁄/\≈o\0\€i≤^€§\–j\˜±}ÆYQñ8cX≥πèVêë\Îä\Ù!éeí¢éxbH$ë\◊\–\◊ü+QæÜ∂&è\˜™¨áz∞ ≤úÇ=E;\ÒÆc¡>≤\Jj¢\÷\Í\Í\Ô˚F\Ô\ÌL∑2>\ÏQFxç\–rk¶J\¬N\œB\Ù\\[µπyV)do\›#∞O\˜G~£ß≠∆ñ\Òà\“$Ü5\Œ5⁄£\Ê\À`{ö\\œi\÷ü>-Õ©XI´^Z¯kI:4@±x\ÊîO\Z@=\Ê\Ú\Ú}ªçkT\ÒNèy\‡oY]Xˇ\0ojrI©k7\—<—ßŸ¢@˚2ñ,ƒû:\‡\◊S¢\Ï¨\˜#ò\Ôì\Ó\ÓÌûµJ\Î\ƒZ^ü\‚\r\Z{¯`÷Ø\‚kòlø\Â´ƒπ˘Ω≥µπˇ\0d˙T∂\◊\r¶\È∞\ﬁj\Û\€\¬cU[õ£˚∏Å\ı\…\‚æ~õO\‘\Ùùc\‚àu-Œ£\·\ﬂX\ÎKs{:¶\Ì05‘Ç\‰|ùYF\—\◊p\ı™°ETΩ\Ù∞J\\ªG\Ó%∂Å\Ûzw\Èü\ÂOèûú\◊3©xõQá\√:U\ˆô\·{\ÕSP‘ºØ/Mô\÷\ﬂ\Ïõ\◊q˚A|˘{~\È\«C\≈j¯fMb\Ò_˚n\ \«Müp	≠\”\\(\ŒI(º`\\‹Æ\◊4∫5=r3¯z\“u\È\Õr|_y\ÒGø\Ò\Ÿ\√a\·ŸÆd:4\”H\Ólc~\’6\’\Á\Ô\Òék3\≈\Zº?°≈¶C£\…o\‚\Õ_Të!±∑≤ªEÉs∑\…\ÊMù´∏r2y+X–©)r•©.qKs†\ÒÅtø\Í\÷˙ï\ÕŒ©\Â¥\‹6˛Kt\n[v“®\√\'ﬁ≥5?É˙±k5µ\Â\˜àeWwm\ŒO\ÍMjxg]\’u\Î˝/^\”m\Ù\Õ^\“8ßh-\Ó\Ò•\Œ”ª\?ëÆÜ¶R©M\Ú\»I)+¢\r7OãI\”\Ìl†\ﬁa∂åE\\6\ˆ¿\ÓOsV“íï+ñ->:eLπ¶˛4¥\‹ñù@û*∏\ÒZ\«^≥\–\‰íO\ı∑:\ÕÃ™±˝4…Øöæ/x\‚OçºO\Z«â¥∏ÆÆ&∞\–\—tª\'\Ò}°\⁄iA˙\ÌH\‹\˜\n˙¬≥uç\r5\ÕK@ºû\·\„˛«π{∏\„UΩvÅ¢è˚!é+\–\¬\‚\ﬁ\›-L™SU4g9‡øÖ\Z7ÇÓø¥dπ\‘<S\‚3	Åµ\Ô‹µ\›\Œ\Œ\‚-\ÿXT˙j/äZ\rÇ¸=\ÒçÕèÜ\„’µ≠B’ï\÷\œq>\‹F\Ã«≤zfªΩ¥ªN\÷\\VX©\Ì=£zï ≠c\'¡˙R¯\¬:ó~Dv6P¿ë™Ö\ÿU~nùOπ≠™e>±îúù\ŸIrËÇùœ≠˙\—œ≠f3ë\–\÷x|y‚ó∫∑∫ˇ\0Lπá\Ï\“˘-‰ò£É/åùè\’\◊R:Ær\ÁVe-?i\Ù§©≤(e¥î9\ı®™^}j*§\ÏO¶S\Ë∏`ˇ\0}ø*)˚O•Ä\Òjv\ÍÉ}\ÈO∏z—öã4oßrnJÑo\ÎOJÅ\ﬁ\’2\Z.ky\»€ør´\ \˜5>j*~i¬ä(¶;Ö;4\⁄(wöZe>êÇä)\Z`/>¥\⁄w>¥üç ë©ﬂç%aEPLß\—GKg;≥˙cü\\g\”4\ÌÕ∑n\„äZ)\Ù∞Xeûv¸ô;ôq¡\Ànc\«sO¢ï\Ì™\Íj)l\·ökydÑ4ñ\“4ë6yFedb>®\ƒT\‘\Ó}hs\ÎE˙\“\–\"L”í£©Ä¶ç\⁄?∏\ÿ]\ﬂ\ƒIë\r?4\Ó\÷¿I\ÁHX\rÁè∫X\?\0)ô$c¯}“íäO]\√A≠∫©h˛\—l\Ùï±ÉF\”a≤\'\Õkx\Ï\‚\ÚŸ∑n\…]ßül\’ˇ\0J\„\ıãû\Æ©â©ÍÆöÇïQ\≈\Àû\Ê\„\Œp1?68´á2\÷,zZ\«y\ZÜê>\»¸\≈\Ë Ä\Ù¿¨\€O\Èæ.\‘<Sñ5˚\Ëc∑ñ˙F\‹\‚4]°PtS\ÔZj\¬6<7 ˙\‰d~Ñ~u$l3\‘~tπ§ûå9PÀ®\⁄{kàè\…F%å+2ì–Ç√µcxW\¬0¯T]Jo/µmR\Ù@/5MJo6yV%+\Zp™2ˇ\0\˜◊Ωn\‰\09\'ßøz>¥˘•k\\N+rΩ≠úV?i\ÚAˇ\0Hπñ\Ì\Û\›\‹\Âè\‰†≠X\\ØsF\·\Î˛…ß\÷^aq˛lß¯˛oΩπÄ›ü®\ﬁ=˝\ıNß˘-˝\”\◊o\„\È\ıß˙≤Ä®\⁄=∞O\‘\ZUâ#a\Â\≈\Z`\ÓVH\‘Q\‹\›Ce\‹\›\\Cinò\ﬂ4\Ó$íx$\ƒUñ[i9\∆®\ÎE\ﬂQ†#o@O\„Lhcô°i#Y\Z\≈èôÜ\∆*}\≈Iê\Û\ÈNçÜ3é(]~\oº\ÍVF~\ﬁ\Ï—öíôö||\94Øqè§¡\ﬂ“ë]dVe!ïX©`r†˚å\”¡\‹p\'¸ˇ\0ç0±\Ã6ì$?ˇ\0¥\ oµ\‘<:ê\Ú\˜*\ÀovŒªècâÅ°•k\Î\ﬁ\”¸M\r∞ΩY{Y\÷\˜6\Õ\ÂO∑]å;\‡÷û\Ê¿Ü\‡V\«E=øC˘R`\Û\«\›\Î\ÌZπ6\”]	Q0\Ì|¶\≈\r\’‘öÜ±soÖ\ıK«∏Xœ™GÄô\ˆjπÆxsM\ÒE∆ñ˙≠∞æ\Zm\ﬂ\€-\‡ì\ÊÑ\Œ#\«\—\ˆ\ˆS\≈hI!Ü\÷\ÓP íCo,\»\Œp£jn\Á”°¸´à¯\„y~#|*–µõπæ—©º>]˚\⁄Vu##≤¨–Éﬁ©9Úπ≠Ñ\Ì{Ñ¨}jÆ±c6©°\Í∂\◊_cπº≤û\ﬁè˘\Á#\∆\ÍåOlf§\rû\'¸ˇ\0à¸\Í^´ë\”÷≤Rqw*\«œæ¯[\„i\·\◊WQ∞\ªh\˜:f£$∫¢\œ•ójõXá\‹¸k—¥üÅ~≥éV\‘\·:\›\ÀF#äIë é\ŸB\Ì_&8îe\ÏMw˚õ÷ù≤ªgé´-¥\Ù1T£\‘\»\ﬂÑtø\nÊ∞ÇF∏æë$ªº∫∏í\‚i\ \Ó\ÿ\»\ƒ\‡n<[T›ß“•ÆI\…›õm¢\nT§ßs\ÎHZõ\Ò®)\ \Ù¿ó\Ò•¶”®\0•¢ù@>ôO†ä_∆óüZ\09\ı£üZ9\ı£üZ\0)\ÈMßPüç%P)ï5E@	œ≠6ùœ≠3p\ı†•¸iõ\ÈsL~4S|¡\ÈE\0xnh¶R*üZEìn¥f¢ß\ÊÅXrTä∆°é§¸h\Ôß\Ó\ﬁO∏˙R\Ô®\˜\“\ÊÄ∏\”\ÛQ\Áﬁù@ßfõFh\ÙRfå\–ø\ZJ(†ä(†óÒ§¢Ä\Ò•\Á÷õN\Á÷Ä}h\Á÷é}h\Á÷Ä∆é}iè∆ÄóÒ§¢Äœ≠?4\Œ}h†	©\‹˙\”i\‹˙\–KIœ≠>Ä\n(ß5\0`¯\◊\ƒRx[\¬:ñ´nÇK\Ë\ˆEeÃ≤$PÆ;å±?ÖG\‡o	¡\·_ù\"fé˙\Ê}\Ô©]2\Ó7\”\»s,¨Xg∏\n:\nOà∫\Ò/Ü\“+,\Íw÷∫§\Ã\€cô†ïc\Ÿ\«J\Ê<E\ÒCKáE∏\“\Ó\Â\ÒÖµõ®$ä\„\“\Âöx$[\“O\√5\—πE(ë∂\ÁM\Ò\≈ZóÜm¥3√∂v7\Z\Êπ~ö}†‘§eµÖByd\…\·01N\\œƒ´}s\≈p¯^{9≠|B∫z\’\‰C˝DG\Œ\Ú%\ı\Áë\\\«\√[€øåüm\„\Òuù›óà4ΩBKy\Ó†Ck,\–‡§±Ç2≤lôON\ıc˛~ª¢¯\Í\˜\≈\⁄Oçd7zg\ˆu‹∑\⁄Ds‹àº\‹C∞Å∏∑\0z\◊O%8¡”üƒâr}6/I\Ò:\ÛL¯õØi:çß¸Q\ˆ≠i`5h\◊\Â∑\‘$å;E3tU˘ïz\ı wØC*\ \€O\r˝\ﬁ\ı\Êzv±\·{\À\·ù;@\Ò7ä,\Ó\÷E∫≥óOù\'ªi3∫Ißï?\'9˘v\◊[\‡-/T\—<\·\Õ?\\ô.5´;Ü\ÓX\ﬂx.;\Ô\ıÆzä\r{£ç˙ò-¯ùc\·ˇ\0â^\”â¥ª]2e\‘\·\’\"{ò\√$\—∆Ü5|üë∑p¡\œ\÷h~.\—<I4±\È\ZΩ¶¢a\0\»-ßIJ–ù§\„5\Õx\√¿ze«à|%Ø\ŸhZx\‘-|E\≈\ı\ƒ6â\ÊM\»\Ò\»\“§ï\»\ƒ\„\0.Mw)v˛gìq˘Ñh\◊ae^Ä\‡QQS\ˆq\Â\‹qrn\ÕmcYÆ!R@\r÷º∑¿\”O\„\Ô\ﬁ¯ªƒ∫\ˆ°¢[\Õywp\È∑ˇ\0a≥\”\·Üi!åu$®9ØOµ`∑Píp.IØ¯5\‡-\„\¬r]\ÍZ\rç\Ê≥o¨jñs\Õuõµñ\ÚVB¡Oß\ËG≠*J\n.R	æ4\ÒU\˜àøfø\Õzíj[µ\”mui¡âÆ\Ì>\Ÿ•\Ó;t>\‹W´¯˚\‚GÜæ\ﬂCˇ\0	™4®Æ\÷y°ñh‹´\Ïp•®\Âé\Â\‡s\»\ı¨Øãö\\∫\«\¬?\ÿ[@eï4\Êí(\∆\À*™(\Ír∏üè\Àcy\Òì\‡µ∆£g®\Ív∂\˜W\Úù>\ﬁ\ÀÕä\ÊO!eÑr9`\Ò©e\ÍÇkzpÖY$\Ù‹õ∏\ÏzßÑ¸Q£¯\ÎEµ’¥\Ëµ=6\ÈôU\„\Á.:\∆\ y3”≠C§¯˚\√˙\Ôä\ıè\È˙í]\ÎZ[ò\Ó\Ì\’]v≤ˇ\0¨TnÑØq€Ωr?\nº?\‚\Î\ﬁ)∫π\–\‡≤–ºC´jCk¢≠qaï]\…*èë≥É\˜kô\Ø¬ΩC·ØàBö\Ôà4++˚õ˝14À®v¢M\À,–π\‹¸˙\‘˚^KõmÉù\È°\ÓJwp9>\’5ªôI\‡g\ÃX¯\…uX±µ\Àf›∑˝\"¡\’q˛\ˆZ∑o.>\«g=\‘v\Ú\‹\…R:\€€™˘ícïçKt$˙\◊ç∑5<\Î\ˆãfâ\„2\Ï\Œ\ﬂ\ö\Î1†,[di*Aû¬µ˛&|Dæ\]\Áá4m√≤xè_\Ò∑\Ÿ\€y\‚4_!Q‹±˙O±\Õex>\◊∆∫\ˆ\Ï\ˆ˛—¥[}[UõU[{˝@ºë¥®ª¡XU\‘\√5\”\‹x?˚K\≈˛\Ò-\›\„-\Óâewoµ™\ÌãÃπEYg∏U∫øw\nóû®\œSí∑¯\Ì.µ¢\Ë\⁄\ˆâ\·˘.<*\˜ñvz¶ßp˚N\‚Ü\›O˙“é\ƒ3û\‡◊°¯\√\ƒ\⁄wÄ<3™\Î⁄ª\»4\›5~dÑny%c∂8c\Û\—\œZ\√oÜ˙Mø\√\‡m*6\”4»≠\ƒv\“¨h\\Hí˘º˝\Á\ﬁ	™\ﬂ>\ÿ¸Q\“c˚c+j÷¨ìZΩ\√;\€3#\Ô\€$!\ˆù«π\ÈU˚â\‘ZY\ﬁJ\Âüx£T¯â°¯Æ\◊R\—#\–&≥i\Ù÷ä+≈πA#[	K)Í°à#∂9Ø9¯\Ò?\√÷ün\ıAm®\Àh-\Ìdc¶\È≤\œX4˚q<è T3©\‰û\«“ª\’\—|Q®¯˛∏4\Õ¡zU\ƒ2\≈{s¶Ne}≤&-\‚UEVf\„{o\Ë˛≤\”˛[x._\ﬁi1\È+§\Ã!!*y;]\œ…ÆÆz0ãÉŸ≥?}Ÿôâ\„\œ|ø\Ò^ñ≠·õã≠\Z\„V¥mICJª\“B=\’CPsM¯c\„\Îˇ\0\›\'X\–n\Ù?i66]\«r\Ë\¬o:2DÄz\‰G±ß[¸;ó˚6\√H\‘|Q´¯n\œ\…ˇ\0â<÷ê\∆.D\\E“™\Óë1¡dVæó\·{ß¯µ≠xÉ1≠∂ß•\ŸYF\r\ﬁlM($è@¸\≈rK\Ÿr¥ç=\„©U€åÒûîµã\·/\⁄x\À\√\k∫jH∫u\”\À\ˆydÃäŒã ˇ\0e∞¨B\"∂wZ\„5$•¸iπ•†¸iy\ı¶”π\ı¶\“`\Ó\ÈO¢:\0z\ÊùI¯\“\–\ÛFiîæÉπ\È@få\”}}∫˚Qö\0}/\„MSøï˘áµ/≠u\‹˙\—G?(\œ-\”\ﬂ\ÈE\0?ßË¨∂\◊x¢\„CéŸ∑[\ŸEy%\√8\ÂdyF>õ:˚V™)\Ù¢WàÆ:äQ\Ût9•\Ìú\Ò\Î@\∆\”3N\ÕE@>µTﬂçC¥˙PN•E>î\Ìï\\¿Cö*|{\n)\Û\‡ˇ\0çç74f†±ﬂç.iΩ:˚~Ω)7û\0\œ\·@Ø©\"Tõá≠FävÜ\«\À\Î€Æ?üª[¶\Â@\—.}\Ë¸j>çÉ¡\Œ1\Ô\È˙èŒùë\ÎLë˘£q¶ü\Û˘\Zw\„HDôß\Ô®?\Zì4\0\ızuEJ¨hz*&}Ωx\Á˙˙S\◊\Â\0û;s@få\”h†fñ™˝∫\ﬁ+\Î{\'∏â/nVGÇ›ú	%X\◊tÖW´-éÉ≠Y\Õ£b”π\ı¶däwß=zQqœ≠˙\—œ≠4\0`\—œ≠&\”˙¯ß\¨\Î\Ë⁄¶†\÷Z≈Ö\Â\ÚÇZ\÷\ﬁ\ÂPRT\—gmÜis\ÎMßs\ÎI¯\–!(¶\‹\\Eio5\ƒ\Û$0CK,≤0Uçeôâ\‡\0$ûî\ÿgé\‚\ÊäEí)]$B\n≤ê \˜A\Ù\"ò~4©MJë~^ºR\Ù\Ó}iôß\Û\Î@N°)\ﬂ\«@EP3Y:u\¬i∫Ü•}u<v\÷\—˛\Ú\‚Y\"ª∑ûö”®,\Ì\"º∫∫ä\Í\Ó`ïv\…ä¨Æ=j¢\⁄\ÿfOÄ\'\ﬁ©w\‚}o\√z\ \Íñ˙Ω\Ú\Àyº˛d0‹¨hîz∏Q˘\’ˇ\0x\ﬂG\ﬁ´g¶NnÆµã®û\Ê-;L≤í\Ó\„\…W\ÃpÄï]¿Æ\‚1ëä\„<\„∂\—\Ôu;\œkW)◊Æ˛\’y§\€i\≈™*˘P\€˘í™\ƒDh†\Ô\Ê&ç˙˙\Î\„t:ú+iqs}•Oß\Î\÷?øM}èk\‹ˇ\0Æ\Ó\Âîs¡\„ä\Ì\ˆ+ôπ=9∫X\Î\Ê¯ë\·õ=&\€Sª\Ò•ùÖ\‘\ﬂfWº\'\˜°w¥nßX)T\Ú5©¢¯ÉI\ÒsI§\Í∂Z≤BB\»\÷7	0BsÄ\≈I¡8=}\ry\Â\◊¡î\ÒéºA©k\Õcu¢_\\^\\¢∆Ænfi\Ìí\0≠ëµV\…\\r∆∫èá˛	>±ënµI5≠BH-\Ï\Õ‹ê$m\‡V\Ú¢U^\ﬂ1\ÀMEX“å}\…jTn˙rS˘\ı¶%>∏\Õ\’;[\rµk\Ë°hç√õªØ+\Ê.\Íò,™;\·G‘öπVt˘í;\»K\·£\‹<\’a\’MC9\Î\Ëó\ZÜuïªXlºB\ˆ\iªìi&]\Ò¶LÄF\rZ◊º?§j_\Ÿzñ≥J\⁄–æ¥∫öq[\»À∞318ÅÉﬂä\ÛkM>_¸\û´kqi\'Üµ\Ì8‹¨ÀúG\”\ƒdS˝\ﬂ,\Ó\›\”o=*˛π\˚R\’<SØ\€\›i6ö∂è\‚\rf\Œ\Ú\Ê˙\ÎPb\"∞Ä\ƒ\Ôd-˙\∆&˘á]\’\◊JåeØ5åüc≤±\Ò\ÁÜ\ımph\÷:\ıç˛¨€Ä∑∂∏e`	\0ä”±øµ\‘v≥ù.©m%*8YcmÆøÉ\ÿ\Ò^}‡ØÖ∫èÜ&\“tª˝SMx~¸Íññ\ˆv\Ô\Ùõ\‰â\'òéU3µΩE/\√[s\ƒ\rt=I5w\˚k7ö\Ì¯µµéI\Âs4®#w$/{”©FM\∆We&\ı=1Y◊Ø™N}j¶ükçú\…$\Û¨+\Â˘órôeêzºùI˙U\»‘ñ\0ì¿\≈vj7∂s\≈9A\Ù™Z&Ωßxí\÷K\Ì*\Ò5Tπí\ﬂ\ÃB\ﬂ\Îc;]y˙\ÛZTö∂\·†›ß“ùN\Á÷ä~†≈ßQ\Ô⁄úùH\Ù\Î\ÌL\Ú˝™óà4¯I4y4\…/Ø,≠nõib\·xOﬁÑπ˚™ﬁ£ëZ;á\\\ÒOçÅ#Æh\Í6v6\⁄uçΩ•ùºVvv®\"Ç\ﬁ*™£µNπ§\œn\Ù\Ô∆ç:$t\Ï\”c4õÜ\›\Ÿ\„÷Ä%¸iRôë\Î\€4®\√÷Ä%\Õ9j*7\Z\0óp\ıßgﬁ†ß\ÊÄ%\Á÷≤m|Ikw\‚M_FéàÆt\ÿ\‚yöDPe\…=@ \Ú=+K}qzîça\Ò≥G*3©†\‹#\„ª\€\Õ?\~§#\œq\\\ËuØYxvˇ\0B≥πéS.±tmm\‰\nv´›Ü=â¡¸´^πäQ\«Ñ\Ìu\'6ó´Y\ﬁ\Ó™f\⁄¯ˇ\0Ä1¸´∞4òüJ%E5\‘W\÷\∆Wä<g°¯.\œ\Ì:\›ˇ\0\Ÿ«ïÁ≠¥[ß∏x\Ûç\‚5˘ä\‰úb∏´ˇ\0èzuèÜc\Ò-«áu[_M7ë\r\Ì‹∂©,ÕªÓ•øö\Œ\«o8ß5®¶?\„%¸\˜´\næ°§\⁄\€\ÿM2Ü\Û\»\Ì\".x\‹r8\‘zóÅ\Ù=;\‚◊Ü\ıÖm\ÔÊ∑∫\Ï¯\»ÿß	ôºÆBéYA\«PEzi—µ™+òNS\ËX\”˛&\\\Îö|ZÜù\‡ü\\\ÈSç\—\›H-bib!2n\«\·]\'á|Kg\‚kG∏¥\ÛTF˛\\∞Œ•7˛\Î\»>∆∏ü¯Ç\√¡z3x{Yö\‚\ \ÁKñh\"ì\Ï≥2\À˝\»T\∆~^8≠\ÔﬂããØx¶\Ó\∆\ÎJ\”ƒê-\Úfxaã3D@1´d\÷u)¡∂£\ZFM-I4{ñ‘æ\"x∫\Â@\Ú-M¶ò≠ˇ\0\\\‚g¸zFPkßæªµ“¥\Ÿu\Î´m3Oãâ.\ÔfX¢O´±\0~&πÖ\Î,\ﬁ∂\‘nW∫Ãíjó<r\Zf‹£\Ëä“∏\nõ©x´˛R3´^€Øóß\≈x°\Ì\Ïc˛#Y¿ê\˜sí{\n\Ê©\Àœ®Gkï\‚¯ô°j*\ﬂ\Ÿ\Î$ç~\Ùö6ó4\§å´¸\Î°\”Ó§º±ä\Ú[I¨LãΩaùUfOf\«CS˘é\≈AbG£ \n\⁄-˛\ıe.Y|&¢\Êö‘îTÄ\⁄)\‘s\Î@>¥QRl\0\ )\‘P\œ˘£5\„Kö)\Î:≤\Ëö´™\»7\«ci5\”h\”v+à¯?\‚\ÔÎ∂ãc\„!h⁄ï\ÂÑZ\Êù%úB=\ˆév∫âr2;w≠oâû\‘|e·ò¥+H-/ØaãSê…µæ\ƒe\Ó√ä\–\Òßág\Ò\÷\ZéóyìØi2\”\Ó^#$>[|Øâ¸Q2®8	ÆòrrY\Ó\Ã5π\œi∂z¥$ææöxb∫\”\Ô≠\·±f!o⁄¨Rˇ\0º\Õ#}pkC\≈M/âºgß¯F=R\˜Iµ\Zl∫Œ£&õ)ÇiWz\≈^`\…PN\Ûü\ˆO°´öá\ıT\Ò5\Ôà5\€\Õ>{∆¥\Z}ïûòí,6∞ó/#nòó;>õjéáo$ü<c;´8oië\ƒ¿d,fiLò\ˆ\‰g\Í*•\À)i\ÿZñº©\ﬂ\Èæ\"’º©\Í\Z‘ñV∞\ÍZ~©uè:k;JÀé≠ÅyxZæ(\Ò#h0ZEkh˙û≥®\ `\”\ÙÿòF\”\ Yùè\›Eì\–wÆ√∑C\ƒˇ\0\Ôµ\Î≥\Ëöfô˝ì˙üñ\ÓwóŒìkh‘û*≥\‘t_\Zhæ/¥\”%\Òï≠ÖŒôsßŸÄn\":2\œ?\r˛≠î®\Á=k+{∆áO\·ΩCR‘¥{[ù[I\Z&†˚º\Î8\Â\"2≥å©Ac÷¥\˜ÅûOA\\å\ﬁ:2Fõ\·OjSûëIßã ?\‡s≤\n\“æ©¨jñ∑R\Î>O0ëEº+®≠”∞=KlP£\Û¨\‹Z\‹f\ÊiﬂçGO©\ÎN\ÕG¯\“\–/â<Uy\·´\»|Ø\n\Í˙ÌÅ∂y\Õ\Êö–Ñâêeë\’\›p03ìQ¸7\Òß\‚\Ô\ÈzÊ±§≈¢^\ﬂ\«\Á\«iª\√DN\Ëú˙0q\È\ÕQ¯±\‚´|8\Ò\Íb\÷[\€≠:\œ±2\‹I\ÌAäÜ¸u°K\·\›yu)Z=>\ﬁ!:5\€!®\⁄Bs\–\◊W\'Óπ¨M\ı;ù§\„Ä2N;z\–ìÄ2sè\Á˛\ÚØ/¯â\ÒKS\ä¸-$:4˙∂ã¨\Ÿ^\”`É˛&1Incvòˇ\0#˝\‹Vﬂå¸od\ﬂ\ı-s\√Z˝£$Ç\ﬁ5%V[Uötç•t\ŒA@\Ó\Ã@	<\nà—îöK®€≤0~$^À§~\–	\Âw)\nEu\ﬁ72G\Ô\»¸\≈zº\◊Úóéº+\·ø¸L\˝œÇ.≥ö\ˆs\ÍpYN\◊\Û\»R\ıfiil∂\ÿ\◊;x\Ù ¯µ\‡i\ÌQ¯\√Ix:\Ìkê\'«ßìù€Ω±]∏öJ*\n=å°+\ﬁ\‚k⁄é≥\·èY\Ís\»\˜>\rπ≤6\◊p¨E\Â\”\Ó\—\Úì®,å†Ü=+´Y¢íh\‚[òZY<H\ÍFAQ\‹`\ˆØ8¯=¨O\ˆ\ˆè¨ã´-Yµk≠V\Œ\÷\bO\Ï˘õ|æÖCT\Ù\≈`jûñ_x™]c¿+æ\‘5cw¶\Î0j1[kQ\Zà¢\Û¢H\ˆêry¨aA98…éS≤\–\ˆßVå\·æS\œ\ﬁ\È\◊˘\Zn\Í\ÛﬂÉ\ˆZáÉ\·◊º!Ø_\›N\“\Û˚N+Öë§[\\™8Uf\ÍEu8È∫Ωkût˘%cD\ÓÆq\ﬁ\"¯\◊\≈\r\·hûkmMH\Ó5…°\»é\Î∫,\ıi\Ï:ìZ7^\—\ÓV¡m¥õ;ã9£ñ\“{;téHt\ÿ@\Á>çU<?}\róç<W†\‹•™j\Ÿ,ø/\⁄\‡x\"P#\'\Ôîhò¿njØ\∆\œ^¯\·\'ä5{ddΩ\Ú\“¡7ô\“-\√\›r\Ã=Å5ø+\ÊPèS5-.v\ﬂ6\‚∏9^H\Ùˇ\09sœ∞\'\Ú\ÎX\ﬁ\”\ı=¿˙Öﬂõ©\Í\ˆ\Z<\"a3ninRf›üV}kÅ¯y\Ò\⁄\Œ;;≠\«V˙\‘\◊6Kss£O˝∂\“ˇ\0´C(ª\Òû\ƒV>≈≤˘é\√\‚§\Îo\£\«.˘]∫˘\Î˛•\«\Û≥˛\r6•o\\ˆ\”F\’e\‘<? \“o˘\È\ZE\¬\ﬂS\Òè®º˙\◊\‚%ñπ˚4\Î1¯è\≈62¯£S\“u&ö\ Iê]	\‰Yv@±gvFGÀå\Ú+foxÉ¿\r\—\ıâ<&\⁄\’◊äÆ˛“ëGv±õ{â\ƒq\⁄@\√¯∑F±\Á\n\◊Z√øg\À\÷\Ê|˛\ı\œ_\‹9Ü@\…\ˆˇ\084ˇ\0Ω◊ä\Ûˇ\0ÖZß\ƒJU¸w¢\⁄\Ë\€?bX6,w˘ÅÇ<úr+ø\˜\œ¡88>VlµR~5;5\0?};y®\È\Z\0ó}.\·\ÎQs\ÎK@U¥\‘,Œ¥˙X∏çujoæ\ÒÊòÉÑ2m\Î∑qª¶Hj√´nÆRë\Ïh\œJ©xkQ\”cÇ\—\À\‡}~S«±\Ù™ä∏=H∫\Ákz®¢haY(cÅds+˘i¥3Áπ•è∑øOzîIí:\‘ﬂ∏\r\˜\ÌúRï©\≈`xæ˚\≈Vk¶i\Z\≈ƒ≥\Ïº\Zïﬂê±√∑™„©¨èá˙ˇ\0ç\ıØ¯∫\À\ƒ1h˙^çtñQ&ö\'\Ûù\ﬁ8\ÊW\À7\›\⁄\›kUN\\úƒπY\ÿ\ÔW4\Ín©![∂éçê1\ı\‰~bù\n≥\»T≥ìÄ†d\Á\ÈYî?æ;\’K=j\Œ˚P\’4¯.7\›\Èè\Z]\¬)â§å≤ë\–\‡\„\◊˚\rB\◊U≥é\ˆ\ \Ê\Àië&∑ê:3)\√\0√ÇA\Í;W%\·\’0¸e\Ò\Ï`∑z^èvO©ˇ\0Iãw\”\n9\˜™åπºâπ\€,Ã≠∏7ÑëüØÆ[‚∂µq·øÑ\ﬁ6÷¨ÆZ\÷\Ú\ÀKô\‡ò.\Ì≤>§©r\◊\«^æ\Ò!\–mu&óVé\ÊK0ãk8ãœçIí%óoîŒ§\ FEe|^í+œÇæ4\Úû;´g¥B\Ì\\Gqêdzml˙`˙V‘†\›E†îïÆç\›Tçºc™\Í\r\ˆàC]B\È\‰?}V\‘<á>Ñë˘\÷¡MsP\Ò7¬ØjzºPE©möb∑ÄFëàÆ$çPË©ä\Á\ı\Î\Áá\ˆ_¥eVå_hzMì†<™N\÷–∏\œ–ü\»\◊}\\Ê\“\ﬁ\ÔIU∑+K≠ORö6^ã_NW\”ß\Òµº\‡£I˙ò©^V6£$cüˇ\0W¯è\ÃU\Õ?\˜óñ˛\Ú)Ø(¯u\ÒÖ|I\\÷\Û\∆$¥èG∂áTk(ñŸãF\Û§pØ\Ô¿O•zà<Ic\\˜G\‘¸A¨ôN\—¡ûeâr\ÃA\·ª\0\Óké4§\Ê£cnec\Ãˇ\0fiùº\‚pxV\Òf§`à\≈˘◊Ø\'\Ù\œ\·\Î_<˛\Ã>\"\Òx[˚?Ü#∫∂\Zª]*ùEaòâ\„Fª{~ï\Íã\Ò\ﬂMΩ\”mu˝U\\”jãX.5%≠Ãßê≠$R2é}\ÎØBP≠(\ÿŒú˘¢vôˇ\0jü\n¥õ∂Ç\€Ws`g\‘˚V^≠Æ\ÈzpI®jVvÇ\‚d∑ÑO:~\Ò€≤\Û\…\ˆï\Ò√∑û(\ú\÷V\ˆ\Ì|ë\›[\›\‹\È\‚(\ﬁ\√~\Ú0}\›\’\…sI\'°£ñáOk$w¯[I†º∂ø\Ÿ\Â¥˙\rp\◊\ﬂ¸;oø\ˆ8\ı\Û§i\˜∑\ÒJm\⁄;k¡m\ƒ\À§meB\ÓåúuÆ\ƒ\¬>!]¯cNÉD\◊\·∏Ç\ÎLH\Z\ {`Sö#<Ô™æ\ñ°\„oÑ˙ï\ˆßfñ7ZáÑ§\ÓÉ• ¿∂≥Ú∂§é{\…<Ådc\ËAØF8h(\Û\‘\ÿ\…\‘w≤=µ`ë§\Às\ÚÅ\œë¨\œ\n¯≥C\Òd\˜O£\ÍêjÇ\ \Â≠n\⁄,í+`©¶G<◊è¸^¯\≈g\‚/Éæ!≤“û\x\∆\Ó\≈V]&\ﬁ:v\◊C4≤3\Z¢´å∂\Õ^\«kic\·\€-V\ÛC\”\–˝£ÃøHm\Ç\ÍF_ó\'\‘\ˆ\ıÆIRpär4Rª≤9ﬂÑZ\Â\˜à>¯Z˚Sûk\ÌB\ÛM∑Nø.Y≥Åé¯Æ\ÀyÆ/\·_ÖuØxD\“uùNŸ¨\Ì\"â-\Ì†\nñªW\Ó˛&ˇ\0k•viX‘∑3\Â*:≠Içröó\≈o\È:\Ìﬁï\‚k=RÕîM\ \Ÿ\0ÆN\”—πÆ≤öë¢\Ã\Úà\”\ŒoΩ*¢áo©¡®ç∫å\„W\„WÑ%º≤∂≥æº\‘n.&Xb6ze\”«Ø\ŒWÆ\ÈVõ≤|πvoF\…\œ◊Ø§¢Rã\ÿ¸iy\ı¶”ø\ZõÄs\ÎESk/Z\\Ì¶µ6ùq$ì[]\ÿ\ dÜ{S∂Lªêì\∆\÷\⁄3Z‘ª4\⁄\ÿV3\ı\Ì\"hW˙M\…\"\»LL\√¯{©˙ÉV\ÏmÂµ±ÇãñΩùc\€%ƒãÉ#z\„µK∞Tú˙\—v\÷\Â\r[C\”\ı\ÎT∑\‘l!Ωç\Â\Ûr6˝\‰Um\¬\Z\'Ü\‰öm\'I∂∞û\·BKqZFP€∂ós∏\ﬂ±KT•$¨òÏÖÜiQqÊ∫∑\‡O\ÊEsü≠\Ó\ıá˙Âù≠¨◊≥^B-\ˆ[©g\ÿ\Ó™¿\œ\0g\È].=äˇ\0∫håöiâ§EkCHë˘h™#rB\Ù´4\ }K\˜∑\Z\–us\ÎE@\n)h§QKE\0RfõE\0QE\0|\ÛöZáqßo4K¯\—¯\”sFh >µK]\—l¸IßΩñßó6¨\Ë\Ï´+#0V\‹≤\Ûèjπ¯\“nß∞	q\€C\rº1•Ωº*©P¶\’A˛œπ\ÓMLØ˝\“E3üZT¢\ÏÆ\„\Ú±b>µ\'>¥\Ã–¨hz\Ó\‘˙b\Zv\·\ÎHßs\ÎL\Õ;\Ò†øxWL\ÒØáf—µh\Z{9ò?\Ó\ÿV\Ô\ÿ\Ìb?\n\◊i›∞•ò\0\0P®\Ï0)¥U\Û;Xc~\œ^[^ò\"{\ÀutÜV_û5pª¿\'èôTYWû	\÷ß4≤\ﬁxgGºñO\ıç=ÑN[øSû˛’ØOJJM;¶)ïtMJ\\“\—\Ù´-%!ø≥\‡Xrß∂F\rY[;e∏[Ö¥Ñ\\\Áwù\Â¶\ÔÂäíó\Ò°\ Ov©t&iûfRXÜ¿]\Ÿ˛\Ôå\„⁄ôœ≠%:ñ¢≤aO;\Õ\Ú\◊\Œ\⁄~ﬂòÆ\Ì¡I\Ù¥\Ï\Ù\˜\ÈK\Ô⁄ù¡5≠M\Ò%™[j\÷j0£TôA\0\˜\√\ÈX\“¸6\µ’´\⁄\›h\ﬂnµe\ÿ!øπû\ÈTu˘|\Ÿ[a°ÆñäµRK®öL\Á4Ø¶ã}k=Æµ¨<0…∏Z\ﬁ\ﬂ\Àpä6\ÙR\«?ùtK3≠«û£d˘\›\Ê.7\Á\◊;z\”h©\ÊadWáK\”\·\‘˘t\€%ªv/$\∆\Ÿw\»\›\À0\Á\ÿV^µ\‡Ω?Z\l\Û.,≠l\„∂K®õ3⁄Ωæ\œ\"@{≤\„\Ò≠\ *ïI\'{ãïX\Â-\Ô<ugò\Ô4ç^ê}≤\”Rí\»\»=\„x]AÆõGõP∫±Y5KKM>\Ò\€wëmp\◊\n£\”\Ã(¶¶©W5|\Œ\Â-	sE3üZ}H\Õ-2ü@¸i\ı\ZTî\0=sû\"ö\ÒºK·∏≠<=™æùp˙Ñó∞\…ob6∑∏Äƒ¶Y\ÃY\„b:\‡f∫jl!\˜\ı´åπ]¡\Ífˇ\0l\Îy\¬®%©VYùolôÅ\ı\Ì∑Z8^Dh\ﬂo(˚Yì˛á¢ö:&rücS•&\Óà|EÜt’º∏≥\‘\ıy!o§ŸΩ‹•èVePH_~ï\œ¯Z\‘\‰\Òäµ8º\‚µ‘•≥í\€\œ˚º¨\—Z,n]dúù†Wh™OC∂î)-\Û3∆¥çE’∑!\∆˝O;¯Åi\‚[Ôàûè\√\˜z\Z\›X\ﬂ\€j∫ÑV\Àqå\"nG˙≥) Ñ\…\… \‚Æ\È7\ÙΩ%tπlt]Z\ˆ\0\–C\‚	\ıº¡,ñ\¬._\‘\n\Ó˘\ı£mW∂\—+-ó\Ã\Ú?\Ÿiø\r~\"i>\ä\ﬂOg.ü5ñ∂\rú¢\ﬁ®\"GÜ\Ù3#A\‰Ç*\Óâ\\ }?\‚m\ı\Ìœà|QxçbÕ®5˚E\Á‹ããçÀò\‘*≤ùΩÅµ\Í[ú¶\Õ\ﬂ\'p\Ÿ˝H4VüZï¥#ŸÆ\Áù¯[\·n•\‡ô\¬iZ’Ö\‘p=\À\ÿ^\Î\›Osc\Ánﬂ±<\Ô(1\‹~eU®>h◊æ¯ke\·k\œÍöï\ı≠¥\ˆ\◊>\\\÷\Ê\ﬁ˙IY\Ÿ\‰4ãµ#É»ØL\⁄})vù∏\Áo¶i}jR¯ï\«\Ï\“\ÿ\Ú•\é\Ì˛\«\‡c®¯sQ≤˛ÕáO]R\‡\\E5Æ–øuì\Àe ì÷∫/\…\‚ˇ\0¯oI\—œÑ\Ù˚\È\Ù∏b∂é\Ú=d%ºÏÉôYYLÉsrF+∂\ŸI¥\‘\À)+45è0≥¯\'zæì¿∑û!µõ¬óup ”ô/≤.V*9|›™®èj\Î≠˛\Èr≥s™x¢\€-æª®Iq\nÇ?\Áû\0$7#5“•>ì\ƒTΩ\”\"µé7\·/\√X>¯v\ÛJÜVπY\ıãê\Ó\›#\Œ!_¡xÆ\∆\Ó\∆\€Q±kK\€X/lÿÜk{®Ñâ∏≤\Ÿ\˜•çá≠IY §ß.i=F¢í≤0\Â\Ö¶çROh≤·Éç\⁄l#kva\Ú\EK\‚/\«\‚kõ)\Â\’5}2\‚\◊\Ã\Ú§\“oL\Ê˚€∏¡\ˆ≠ö))\…Z√≤j«ûxá\‡Õû∑ß\ÍÇ\„[\◊umRm2\Ê\¬\“mb˝•ä\ﬂ\Ã^™àv\‹k∑\–\Ù≥°\ËzNú≥yˇ\0a¥Ü\€\Œ#˘q¢Éè¬Ø\—ZN¥\Í.Y=£\Íâè$RC/Ô°ëY$G$¨äÖîûA\Ô\ÕgxCá\√:ÿ¨\Â∏kUrb[âã¥1\Ù\Úêˇ\0pô\Ê¥)\‹˙\÷NM\Ó\ \—l\"Tàiüç.\”\Ëi!í”ï)§\Õ!\rJì5\Z”≥H“•74¥\0\Ó}h£üZU¶©\ÀM\Õ>Ä\nw>¥ô\Ôû)FOCö\0ZuPE>ä\0(•‰Éúj;g<Pa¯\“\‘WV\⁄}∏∏∫∏ä\⁄\Îñgªò\·W\'åì¿\ÕKL\—EÄ3E2üö\0(¢ùö\0mQ@8\Ó£uA\ÊZwô\ÔAeè3ﬁÉ&ﬁºU}\ıô\‚/i^\r\“\'’µª\Ë\ÙΩ>›Ç5¡\\Öf\„G$\„µ4õ\—\"à\ﬁ\‹iŸ™\Í\‚kxßÖ\÷XeéD;ï\∆3¡x9•\Û≠;5∏˙\\≥\€9\‚ïXz\÷E\˜â¥]\'Sµ\”5\rgO±‘ÆÄ0\⁄\‹\›$r>zmV ú\‡\Ù\Ù≠7S2∏*\ pCi\Úæ\¬–õp\ıß\Ó98\«_\Û¯\÷&ø\‚ç?\¬:lwöå≤\"O(Ü\⁄\ﬁ\›|\…n$#!#QÀ±ÜMW\èãì\≈\—j(t\Î˝\"ˇ\0Kª˚-’Ö˛¡,{£GSî\ı\Îö9ennÇπ\”fäÅ%£?Z~˛\›ˇ\0\√ˇ\0\÷*FNî\Âa\ÎP›Ç9ß\Úqés“ï¿õ>\Ù~5;4\0¸\”\ÛQ˙ø>î\Ï\˜\ÌN≈í\Ó¥f£e)ç\√nFF}?\…πêxˇ\0\Î\‚ê\ÏI∫•\ÕA–ÉR\Ïm†\‡\‡\Ù8†á°©©\ÿ\Ëz|∑˙ç\‘V0\„t\”HW$íNI\0{öµ24o$gÇßw8\«\Î^O˚LC>©\\≈t;W\Ú\Á\÷/ñˇ\0\‹X°ñ\·â\ˆP\'“Ω\'G\’\ﬂ\ƒ\Z.ó©»ªn/≠ ∫uô\—\Á\Ò≠eM\∆\n]\»Rª/fåèZk)SÜCM^1û+\"Ö•§ˇ\0\ıS˚\ÿ\Ù4¿e-Eq{igqioqsÖñ\⁄)$\n”ïò \',@8\Ë*pA\È\Õ@\nóüZjgì\ÿu˛_\Ã ó\Ò†b\”\È´RfêÜ\”\Ë•J\0uIöm\0˙T¶\Êç\√÷Ä,“•)Ü@(¿}\r,|\ÙÊã†%¢ì¸ˇ\0ü\»‘¶&Tú0m§w\”\Î\Õ+åmQE\ƒKû3\€÷óØJ•´k>\“n\ım^\ˆ;N∑Q$\◊WNT\nI\«\ﬁ }Hop•H!Ä é˘ò•fú˙ˇ\0ú\„˘\—Yø\ëiq¯ô|9\ˆ\Ë[_6?\⁄Mb?\÷}\·<\Ã˙\‰É¯ä\“\»\‹y\Œ1N\Œ\ˆ`>ävhZ\0Q\Ûc”π\ı¨\œxßF\}úW:\Ê´m•[\Ã\≈bêf#®ç,FJ≥§\Í6öÂçµ˛ùs\r›≠\¬\Ê\·\Ë\«8«ø<}i\Ÿ\ÿ.\\U©;g∂3¯SYYWqR8\…g\≈S˛÷±˛\›M\Ì1lΩ°\‘\œ˛Zò7\ÌiÆ0sOP\Ëh~4w\«|g\Ù\Õ©›å\Á˙:\Êºu¨_xf˚¬∫è\⁄%á@èQñ\r^\⁄(K\Â%ÇO*V\0d™Hü68≠	]å\Í(®/µ=>\Ê\ \ﬁ\Í\Ókã\È+X¶ëUÆs¨`ú±U‰Åúj\ ˝\“\ﬂ\¬I\ÌèZB¯\—¯\“`ÇúÅÔé¥¨¨π ë\ıµc\Ù©ˇ\0\Zç~^î\Ï\”\Ùµ\„K∫ÄE˙\–\Ï\»==\Ë\Ù\Ï\—\Âø\Õ\Ú∑\À\˜∏\È\ı¶\–üç-6û¥\0ï4`≥\0I8\0T5,w+g\Ê\\ø€°ôâ\ÈÖ≥\Ù\‡˛T÷Æ¿\ÙE]7X∞\’\·íM6\Í;∏i y#/ôm`˚\√^*\‘\◊P\Ÿ¬≥\\\‹Cip$ô\¬)¸Mpˇ\0ld±¯[\·£:\‚\‚\Í\◊\Ì\Û`rdôûSüƒäΩ\„\r¯5Æáä<Uaß\Ãt\€vÑ\\\Íqâ\„é?_-Énnµ£äS\Â\Ùπ\’\€\›[\›m˚4\]n\Â|ôC\Á\ÈÉR˚Wì\ﬂx\'IÒ•¨É\√^∑\Ñ2(?\ï]Ÿ•ï\ƒ`\Ù0[&$v\˜∏U\Ë:˛∑k\‡üj˙‘®\˜∂\⁄EÉN\À)˝\‰\ÂW\‰˘∫÷≤£\ \“\Í\»S\“\Ê\”™åSO[yDa\ÃnÆ\Ìßù|\Ûgq\Òä?\nYxßRÒçñï{\‚õ˚M9l§”ôÜè\Á\…¡Ä08\Áû\’\Á\Î©]xW\‚ç¢¯ã\Òè\≈\⁄~°§™∂ö\\Íóm\Ë!\ÿTè•wC.sM\Û£\'^\›ß~(|J\—>¯J\„Z\÷\ÔZ\⁄wäD∞µÑnû\‚P∏\˜·õ†\Ô\\è¿ﬂå\Z\'éº=•iÕ™]\‹xû(•∫]F’≠\ﬁWaí\—nz\‡u\È_8]\Î\Zó\Ì\⁄k\—˘˙ˇ\0à|CçmmÇ´cß[¢<\ﬂ/\˜úñ\…\ˆ5\Ó⁄ñÉoy˚Bx3\√˙,1\≈Ñ\Ù°-\ÿE\‹\÷\ÒmaDˇ\0xÇ>\ıv\’¿Q£Gí\˜2çyJW[ø\≈;(<Pû\º\Ÿu‘µ5æîo¡[\0˘\»\ÏXÅüRv\Î\ÚÄO\0åèq\\Vã2xã\‚Wàud]\÷\⁄2&âg!\ËfK¶˛c*ˇ\0¿O•jk^&\‘,\ıe\”to\‹kwÆûu\≈\Â\ƒ\Îcg\Ùiä≥H\ﬂ\ÏØ5\·\ \r\⁄\ÏRM\\\ÈI\«\'ÅGp;ûû\ı\Œ\Ó\ÒîÀèµ¯kJ?›Ç\“\Ê\ıøÔ¶íX\˜\ﬁ\ÒΩ\Û~\≈¸¥K[!o°v|V<æeør;é¥TV±Ωº1#M%À™™˘\”c$˙ëR\‘\0˙ómER~4\0ªh£ä\0˘~ç\Ù\Õ\‘n¥?q˛\ıx\ƒ\r>\˜\„á\∆KüAt\œ¯v\Õn\ÊdB\≈\Ê/\Êa‹è0`{ä\˜ú◊ìx£¡û+\\Ô\ƒ˚\ﬂ¯:\‘ˇ\0µ°é\€¶âcmä¨ã!É(Cï<\ˆØC%æ˝*\\≠\¡∑æ\ÒØ7sø\Ÿ`ñ\À_”¶ê\ˆÑïEù\Ã)úà\›$pk⁄ó1»õ¡\…¸=k\≈<I\‡/¸H\Ò6ó≠Káwñ±y\ﬂ\Ÿ\Í\œq<\Òˇ\0\n\ÏãJ\ˆ&ΩW\¬~∂¶É•\ËñwWV∂h±$\˜èæG\˜c\ÈO(π©\ﬂpß{jy◊Él¸+§ˇ\0\¬n\ﬁ8\‘l/\Ó\ı-z\ÛM-™4M4÷∞ê#\\,π]\œ\√çI|¶≈©•¿û,=\⁄∏ñ\ŸeqJáïs\\ÁúëXü$˚gÉd\’\ G$∫û±©\Í	6\≈8r\„\Â<\„Ä?1]\Êˇ\0ªQ^¢n¡æßå¸J\Òn≠§˛\—_-≠\Ùa™°∞î\ÿ⁄Ω…â$∫ò∫∫,É\€\"ΩW¡~>\”\Óæ\’v∫éØ®\›…®jWj\n\«$\Óv\∆!UTö\Ûˇ\0â^\‘<E\Ò=F\∆ñ\˜J\º∑z]\‚°\ÿ/£ΩI2}Z2\√N\rz6ã\‚{O\ËZ≥G\nkv©wo0´.x\z\„•]i~\Ê*\"á\ƒ\Ój^Kx∫|\√O}∑\Àc\⁄ŸºØ3˝†Ω´Ü¯wÆ|C\‘<q\‚õˇ\0açKh†€ßá%í4ö=á¯ìn2ªµm\…\∆\Óû¯\Î^}\·Ø\Zh:oàæ\"]j:’ÖìÀØ$!.\'Q#¨6ëF•W9#Ç8\Ù5\Õ>F\ÏSïô\◊x\„^‘º7\·-_U\“tñ\◊u;8’¢∞\\\ÊCªhúx\ÌR¯\'ƒìx≥¡˙>≥{ßI•^^[´\\\ÿ\ \n¥ré£ëöüI‘†’¥¯omDæLªï~\—B\‰/´\Ú*·ê±ã>\È8¿¸c},Yi\Zùø∑zÆØRC Yî∞»§\Ò#\‚ú‘¥]>Iµ+˘§[\À¯-\–\»\ˆ∫Z\Ò=¡Q\»\„ï\'ä\Ô\ÏÂâ¶∂ïgµmé≤FC+©\ËAk\Œ>x\˜\√wö\Ôâ<O-Ω\˜ã\ıŸú\‹\Àn\Ì$P[\ÙXõù§ußiñ$¯s\ˆNÖ§[x£√°ò\È\…6†-n4\≈oΩn\Ï\ \ﬁdKÿä\Ípß—ô›ê¸ºº\”¸?\„V\◊\ÓÂÖ¨|I®âØd`çU∞\'¢( ˙sN\—>>\Ëæ!\Ò4:fï£\Îw0¥\ˆ\÷\˜:Ñ–à¢Ä\\0Hi˘\\‰Ç8\Á#°\'\√\ˆ‘æ\Î>\‘5]G^iÆ/\ıQîbQO\"5\⁄i‰ä•≠¸2\‘¸S´¶°©xõ˚ò€õ¥\ÕªBo^›ï†ë\Ã\“H£n\—¿J\“\nã¯ùànkc´\ÒOç\Ù\œj>\”/\Õ\”j:\ı\Á\Ÿlm\Ì\·.\\èºÕÅ¬é\Áµq1\Îzá\√?¸]’µàØ/¥\‹Y\Í\ˆâÅY¸»º®ˇ\0π\ÛØ#÷∑/æD⁄ñáÆi:≠’øà\Ùy$\Ú\ı\rfFø[à•èd±:3\r™Wº[H5°ˇ\0ä\Î6∫\ƒ>\'∏É\ƒ	™Aú\÷\…l÷∂\—¿å\Œ#çC≥èùâ\‹^úUyï\Ô3\Õ˛*7é4c\‡˚\Ì~]/W7o}cïcj\—5Ω\≈›ú∞\∆RVr\\ç¯\‚Ω\‚àó\·_√ªãª6ç\Â\”\Ì\‡\”,‰ëÄåJJCπ\Ë`±\'†§\‘>\ËZú0˘ë\Í\Ú‹¨ñ∑\“j∑3Oi ˚Ø	ï\‹)\ıµo¶n\—≈Ü©9\Ò\0e);\Í1F\∆qªr\ÔUU\\èQJ•jr\ÂV\ÿ9Z\‘\ÛØÑ\Z\‘\÷.\ÒÅmºAã\Ù}\Œ\⁄\Ê=Y§\À\ˆâ\…\Ûbﬁ§Ç°Å\0˙É^°g5\≈\¬\œ\ˆã_≤Ìôë?x\ÃA\—\Œ:j\Áì¿∂Zoà¥\›_Cï|<\ˆ\—}í\Ó\÷\ \—>\œ}l8Ö£\'\‰ ±√©5\‘˛5\ÕZQîΩ¬°\Êp~3¯Ög¶¯õK\“l|S\rã\ÿ\‹\ƒ\Ê\Œ\r&k˚áçì1ƒ¶8\ #`ÇrkÆ\–5\»<I4Ü\÷\”SÄ.\ﬂ\ﬁjYn\œ]¢@3¯U¯\À[¥\∆!\‰¥\ÏVåΩ∞à	 gÄ\r=Y_rª≤Ü\Îé\ﬂJM¶¨Y\Á≥\”|cÆ?\ƒM^{xÏ£∫k_\…s0ä8\Ì£gVùr@\›1\«\·^Ñ¨£\Ú∏ß±°\’\‡æ¯oo\‡\ˆµ\”¸Y°\›¯û]>(\ÏM\·\«\‘\‚íVµô_á_ºêk”æ\Ëw~\õ\⁄\\\ŸI•[=˝\’≈ûï%¿ú\⁄Zª~\Í2ÀêJ˙f∫´“ÑW∫Ã£\'-\—≥™\È\ﬂ<-Z\’\ƒ\ˆ:ïçÿüF\ÚêE¥1ÜY\œ}\Ì3°\≈wkIÄ™\ÃOL\◊™x\ˆ\Î\∆Wû!\”¸W©iñqYKv\ˆ\˜\n©n#,o≥wzªÅ`í\’\‚\’5\ﬂkâ\"¸\Îw©¥*~â\0åŒπ\ÁÀ°ZùA\‹i7cûzTï^\ \÷->\“;x¸´Xc$y$–ì\…>\ıc5Åc≥O\Á÷¢©?\Z\0íäjS®\0°Héeb7.\ÓîQ¸T¿\Ú|;oázmßât\ÔxßQ\◊Øk6Z∂™gáR/rä\ˆ\‚\0!f r\0\'•{Tñ\Ó\◊!\’[Ç£5\Ê⁄Ø\√]c\\\Òó\ˆ¸˛:‘¢kg\Ï\€K[u[€çàdYA`:9≠\Îo\⁄B\Í\Z∑àu¶Z\˜Zù3ˇ\0\0á\ ZÍó≥î#w©:ùπ´7Ü4=SX{oµ2\Œ\‚\ÙDx\‹bÖ‹°π#ä\·æ\\xz\À¬∂V∂û$≤÷ºE¨\"\Í˙öˇ\0h\«,\”]\Àâ@ƒ®R8P+¨\ØÜ4o\È\Ê\√F∞é\∆\ I^y-\˜¥ª\›\«Õí˚∏+\∆+Õø·õ¥´8~Õ•_\€\ŸZ¯Ô¢∏ìN2\Í6\€%\Û<´{É0US\˜N\‰\ÈE5JQjNÃâs#ÿø\ZZWeiôîawt°+à\‘\Òok7ˇ\0>/Yxq|E\‡\›ì]Üyçµ¥öõ©\Úƒìc˚¥e;:\ÔS\∆EjxV\Ò\Êó\‡+¥\÷n¥\r2µŒù{q47ì\À§ym\"\Âó\Ê∏\Á•zFó°\È\⁄ﬁÆùaob.\ÓZ\Ú≥\«\ÛO;p\“;\˜à\È\ÿVGã<o\‚/¯\÷\Œ\◊zóâ4Á≥ö\‚BJyQ∂;q\‘\˜ØV8ön*õéà«ë\ﬁ\˜1˛\r¯vd\–ˇ\0\·4\÷Iü\∆>-ä+\€\ÎÜ^ Åó6\ˆ±˙*+!lwZõ\ƒ⁄Øâ<Y\‚çC\¬˛‘ì\√\–\Ëøf}_Wö\›gy\'ï|\ÿl\·S\–l˚\Õ\ÈZ∫F±≠…ß\È\÷m\·i\Ï\Ô`∫û˙˙lÅUU\ˆ4rI#\Ù8»®µ¥û \‘\ıç#\ƒ:∑án5Eà_\«d-\Âä\·£]ä¯ö!Çq\\íó4õfáe#ë\›xGc≥\\ÎF\·\ÎXZ?ám¥ô\·\Ó/µMET°\‘u;É,¯?\›\«»ãÏà¶∂+ú£ó÷¥;˝\∆¯\€Mé\ÀQ#NM6\Ê\€P∏\“D®\Œ\Í\–N~U$2>>¥æ¯Å¶_¯K\Òã†\Íw˙T”¥Oc¶§m,k\Êa\ﬂjí≤å\Ú\nqZû \æã\‚®\ÌSY\“,µà\Ìã4Q\ﬂD%Tˇ\0Ä0\⁄Zv\Ò•™GQG1ç´Iµ<ú\ÔZ˚Eeu±6<·èé\Ô\€\«öüã≠¸ca´\»5’í˛\¬\È\ÏV6}∂v\[Fç\–r[∞ØB\÷<7\≈\Ôh∫äèxb\œDÇ\‚1™¬ø\Ÿ◊ó2\ SjF¨7¨J™\Á$c-^å≤À¥(ëïG\\\Ê3KÉ±y≠eàå•\Õ\ÿJ6\Íp‘µ¯|7/Ñ5\'ø∏\ÒM´À•«´,\r∞Zc\‰Ωy\ÿlfX§ 9.Ñus\·À£\ÈZ◊Ö..¶Ωì\√Z¥∂p\\]πíY-\‰hYâùí2˛ªq\Û+\Ú\Ò∑\0r~¶¢é\÷y\Áô Hß∏*\Û8\Î&\‘\ÿ	\˜£\⁄&ûÉ8Mrm*\ﬂ\„dZßàÆ≠l†\“¸?z4ó“à\‚3\Àq3\\4dê<Õàãé∏a\Í+∞\Ò?á\Ì<[\·ΩSCø\Û>≈®@\–Jbb≤\0za–ä\”\‹v®qº\«\˜aä˝7\n\\\Ù\˜\ÈP\Á{x∑\≈+âzOÜ\Ì-S\∆p\‹h∑∑io®\Î\È\ÚZ\›\⁄¿(díg üº¿bªO¯£\√\Z?á¸5\·\‘\Òå>!\’IfóL\“I-\‹\ÿ%≤Gp\'\ÿ\ZÓ£ë\„m\ JrÑÉ˘c≥|e°\≈\„M6{\€\€\Ày≠g˚Uù\ıº\€\'µú\√&Tˇ\0A≠\ÂZ5\"£5±ü+ãπ§≠\”\‹\‡{\”\ÛU\Ì\Ì\ﬁ\⁄\ﬁ\Í{ô#çQÆ.6ô%\«R\€UFOµK\\ÜÑ\‘QE\0;üZ\≈’¨ºMw´\”5\Õ7N\”6™≤\\içqp®c*ä\⁄\Á÷é}húø\ç\Ó≠u§O®x\«^òX]-–∑≥hm-\\ØTdé \≈Mt\‘\ zP\È\‹˙\”i\‹˙\–\\ø\≈MY¥?Ü>\'û6\€ssd\ˆ0\Û\Ê\\b«∏/ö\Í*\ÀmBŸ°ªÇ+\»w+˘wáîñS\œ˚J\„UrªÉ\‘uÖÇi∂6ñpç±[¡	\Ïv’ïTh\ H±ºéÄÜ˙ÉHä[©\«÷ü≤ü6∑C\ÈcÇπ\T¢\ˆWÉ\¬Vó;5æ°\·\Ìdicg\ÜåFkcA\—u≠G\¬\˜\⁄wçd\”\ı)/Lê¥6\Ÿ;m\œ\›Wóbñq˝\·\≈t¸˙—ÉZJ¥§ëü*8\Õ\'\·nâ¶\Î\Zf£5ÓΩØM•ñ:tZ\Ê≠5’Ω£të\Âwut\Ì¶\È\Û\ﬂ}∫}\'Nû\ı1ãããH\‰îc˚Ø∑?ò´õ)\€(\ˆ\’/{ï è\Ò\Á\Ï\Á{\‚/à\⁄V≥\·\œO\·ùµ\ÎIX\ﬂ.˛-∏⁄Ñè\‚5\‹X¯kB¯\\˜Vì\√\ˆ≥Ku∏\ \◊Zåøhº\‘odmëy“üöB«ÄΩw{+ƒû\\\Ër-\‘vqiwÜ\Ù\¬\÷\ÊUï\Òµq\ÛÆ~\\'å\◊L±ï*Zà\…RÇ\’\r\oÜ«Ö|3aß\Ûn£O6\Íc\÷i\ÀnëèÆkyws¿\Á\Ô{\”?ã=™Z‚îúùŸ™Kaî˝¢ä*F;üZ(\Á÷ä@>üLß\–\‡˙\—M\⁄}h†ñ7R\Áﬁ£\‹}(\Õí\Ô°K/Cöáyß+\Zw\“\ƒ\Úì+Zñ61µA∏z”º\œ\Áè∆àãb;+]2\÷;K;hm-\„˚±[\∆W\'{c¶≠\‘)\◊\È˚\ÍÜX∑∏hdVú|\√¯}+ù\Ät/\¬\–h∂r[#|ä\Ú\\I3\"ˇ\0u76V\ﬁ}\ÍO\‚\«J9ù¨#;^\ûá‚©¨•\÷t´mM\Ï\Û\ˆv∏B\¬<˙åç\’Öº\·ˇ\0µ\„hZ=ûù-\‰\∆\‚i\"Cñc\ı\Œ+c\”ﬂ•*Q\Õ+Y2πQ>\‡\Á,CR8@)€á≠@î\ÍÇI¸\œzr±™Ÿß\Ó†9\˜•Y*æ˙}-%IUíJó\Ãnz\2}ø\Œ\r¢&ßnµZ[à†ÜI¶ô-\·åny$`™£‘ì\–pjV˘´|§u¸˚\”j\‡âóé¥π™\˜v\÷1¨ów0\⁄\∆\“,J\ÛHcÖPOrz\ı;+#`UáPF=)&iŸ®≥O\ÕøÄ{îõá\ı\È\\\Óª\‚õ\»\ıi4?ië\Í˙˙[%\‘\Ìur-\Ìm#v;\Œã3*±\n9 :Q\‡ü]¯õL\‘•gù™È∫å˙]\ÌΩ¨\∆Hå±\˜V=çh\‚“ª\'©\—)o∫(˙\“n>¥’ìwN~îΩzsY\ﬁ\Îp‘ë)¿`†eèA\‹ˇ\0úS\Z\«\Ò\’\≈’ø\√\ﬂMe#\«yèy,/\0\ \È≤∞˙UF.rQA}Ä6r$uˇ\0?ç-s?µ©ºC\\Ô¬öµ”ôno4´Y\Âï\«W1©~>™\√\Í•t©JI\≈Ÿçjâ≥KLßfêJ}Fï%\0%\Ì\√÷Ä&éüLéüπ\‚óq\⁄)\…Lß\ÊéQéZzT9µ*g\0\ˆ\„˘\„˘\“Zåì4Sà\‰Ä©=)RTìyäX\ÁªD˛[\⁄\Î\˜î\„°™µ{\0¥˙e<)cÄ2iuSΩ=˙~x˛á\Úß¥,üyJ˝F+¯ªC_\√\·è\ÌK_\Ì\Îã7\‘\Œ7˛Lo∞ñ9˘XíN\ﬂcUg\ÿf≠JµF3û)„ìÅ…©‘±\∆\€wm;så\„å˙T\\\s¡\È\Ô\\_ä-om˛,¯U]FH\Ù˘\“\ÁHìLq\ÿ¡=«ò}«î\0™Ñ\\ùâm#ª¸kï¯è\Ò&\«·éô£\‹\ﬁZ\…z˙¶ß\rä[\¬\‡2©\0\Õ?˚±ÜRONG≠uK8%T∞T\‡t \‡è≠y?\∆)aæ\ÒTvS®ôm|™\Õï\Œ...m≠°#˝¨ê£æH≠\nj§˝˝âîπVá}\Ò\ƒ\À\ˇ\0¿~(\Ò,±ï\—leπ11¿v\‹\‰í\0\…¥4õ\Ÿ/\Ù]:\Ò\‚=›¨W9π7ü^Eyø\Ìe®˘\ı5w7\ˆﬁ•\rÜ\ÿ\∆K\ÛnèR\∆P;ízéüßΩ•ΩñùΩX\√vª¡\‡T\\ˇ\0:πSQ•u`•y4Låv\Á∑Lˇ\0ü®¸\Í\rgT∑\–t]SVºfK=:\÷[\…\‰Qì\Â∆õèµó\·?\Zi>3\®\Òõ3E£4≥¬∑Wõ Y3yFBsÄ¨\ =k\„ç…≤¯#\Ò	åãcK\Ê8\‚F\Ú\…˝G\ÁYB<\“QeJZ]nï©E´\Ë˙u\Ù\Ò¡}o\ÃI(√™»õÇêàzUµ¨ã?xK\ƒW˝Ö\‚-*˛˘\"éµV\⁄\n<¶;Ü´TeópØÆ8®íqv`µW\'¢òåz\”\}*F;üZ(\Á÷ä`˙`˘àì\ÈOèπ\Ï:\–\È\‹˙\”{„ø•;üZ\0)i9\ıß•\0<eÄ#êy¸˝G\ÁN\‰Äs¡\È\\\ƒ\”xØP\ÒÖ\Óùesa°h∂\ˆêŒ∫Ñ∫{^\‹\›;å∏•Pò\n:˙‘æ÷µ;\ÕC]“µïµñ\˜Kö0n\Ì\«\ƒ2«æ\'*~\È¡èCZ˚7\À\ÃO6ßGÉ\œwØµ?Æ8ˇ\0\Î\‚±¸E™jZ}≠¥z>ó©™\‹\Œ ã\Ìì˘6\ˆ\Í9/+™3S\—WìU<5≠jó∫Œø§\Î1\È\‚ˇ\0Jí(\ﬁ]4øï∂X¸¿0\ﬂ\ƒ=)r>^a\ﬂS¢¡\Ù\Ó\Á“ùúÆ\·\˜}kï\Ò\˜é[¿\÷6B\œE∫\Ò±}3Ei•\€\‹, ™2YC¬™Ø<\n\Û∏~4|AóM÷µ\Ô¯EóKà\›À†\›Iw-¸\÷\„˛ZG(]¨=\«\—O	V§yñ\ƒJ§b\œnˇ\0øè•/©\Ù\Î^e\·_â^-\Òñóßa£¯CSÇH\÷Gµ\”|A$ó0+\ÙI\Ï˛Z∏˛\È9Æ\Î\√z\Ï~\"Ñ:[\Õcyøgû\÷\„\Âí)0\Œ;`Éüz\ T•i•l%üà\Ì/|I´\Ë\	>◊•¨&\Èä¸§Ãª\‘/\‡A˙Vò!ÜG#÷∏øá\Óö∆µ\„u⁄ö\√C˛\ÙvÍ∞Æ\ﬂQ¡z\Z\È\ıhælk:ﬁõ§Kå˘W∑q§≠˛\Í	¸*e•d\nI¢\Óy\«Jz¸\›~ï\«I\Òã¡©\'î5‹ü\ÔGcr\…ˇ\0}´_E\Òûá\‚I§ãL\‘\·\‘%åe\“=ƒ®\ı \Ù§\·$µE]TQEf\È\Ùƒß\–fä~\⁄(\‰\›‘øçEº\”\ÛAcø\Z]∆ô∏z”ø\Z\0In§ñGX\„ç\ZGv UÂòû¿w5èÆ¯\”N\–¸s\‚ø4\Í:*Z˝©f∂˘å\ÈªoÀû˚àw\‚≤|yp˙é•\·\œ	D¡ü[πfæTl2YBõ•>¡\œ…ûÑ\Ò÷∏?iáE\÷u?´©\—|[uay¶\Ÿ !mâ∫AväO\ån”ö\Î•F2›ôNM\Â\Êy©Ä\ÌFí)˙åÉ˘T˛[yfMßg\˜±\«\Á¯èŒ™[\⁄[i∞\≈koCekä$F\ÛbÆ\—\˜∫ö\ÛœÑ˙<\ﬁ0˚\'\ƒ\Îª˚∆º\’\∆\“\∆93≠ô˘D%zA\œ\\\Z\Œ1\Ê\’1\È{Ü3û=k\ƒ>=\“<7™[ió\Í⁄ú–ãÉe•YΩÃê\ƒzH\·*ßì\«£©jñ\⁄<m-˝\‹VAGv\‰oD^\Á\È^u\·\ﬂhû¯\Õ\ÒN˙\ˆ\˜\Ï2µÆåëC$N\Û»Ü’§a*7ìúe@‚µ•MJ\˜[ïèM\”u[-kM∂\‘4€ò\Ô\Ïn‘òßãç¿0>åv´h\ı\ƒ|8\”\Ô\"π\Òn§mf\“\Ù}cQ[\À\r>\Í1±˛\Îl≤¥cò\À\…\Ûl bªDÆyEE\ŸrUcN\›L\Õ;5òá~5Z\„V≥∞∫∞∑∏∫[yo%hmP∞\›+*ñ`r@\Ë5>kêºñs\„ëfW\'√ö%∆¶£≥Ku7Ÿêü\˜U$?F≠#`go∏z”≤v\Ó\«∏®pv\Áz◊ó_¯∑\∆~+\Òwè\ÙüjzWÜlº\'µ\r\›\ıí\Œ\˜sî\…W.@D\œ\Ò*©\”u>\\≠π\Î∂q\ı\0~=+ë¯µ\‚i¸†¯oUKi¯ßLÜ\ËÆ\0{vg\ÛW\'\‘s\Ù¨}[\≈W~0\—~\⁄\Ÿjç\·\»<R\Í˙Ü£g\"´¡ã_0Z´7“øûs¿Æ3\ˆè¯k\·ˇ\0á+ñµ®-\Ì\’˝ºm¶jö¥ó\∂\‡<\÷\»\⁄\…+¶ñ9.gπ.V\ÿ\ˆäñ1\Õ\\ﬂ\«vSå°\—opy ∞â\ŸX\ÈZ\k0/Mø∫∏ä4πÇ\’U\‰p¢GïSn	\Í[∂:\ˆ®¸Yfu≠\'ƒödO\‹]\Ÿ\›Ÿ®\ﬁ\Ÿ$â\’A\ÙØ/º\_ç<a\\„A\”$µá\√W^¥\”\Ó,≠nÆcëØ\ı+U_öWåêëúºVp¶•X˘èV÷¥=;\ƒ\⁄=Êì¨XGß\›.\Ÿ\ÌfN\rª*x*GcVtªX\ÙΩ6\÷\ 	.$∂∂àG\‹\Ãe}£±\'©\˜Æ*\˜\≈\⁄\Ôã\Ùªª?hZ«ÜºG,±˘óö’Ç-≠û%\›+8[åØ\0!5\€¬≤¨Q	\ÊKâïTI4qyh\Ï:∫&\ˆ+üC\\\Œ.;ñZZv}\Í<èZ*@\Ú¯\Êoá<I5≠Æ\ÿu-K3kWI#\Ÿ\È.$πãŒùP}\‹◊é+\‘</\·\€_h∂˙uùƒóã#=ƒó≤∏i/eë∑4\Ó√ÉΩ∏„†¨ÀÖÇââ%¬âSZ\–>\ÃcôG+[\\é‰âú\„\–\ZM¡∑v\÷\‰\“\ÏMPÑ\ﬁY\¬G_$oI\"É}w\Œpú#¶i4`jü¥/É¥_]hrjë˝í\˜\Ï\Íe›ß\√0\Œ\‡d\rû0s\ÈÉ]Êµ≠\È\ﬁ≥{\ÕWQµ\“\Ì#q∏ºùaå±πà¿\'\„\˜ﬂ≥\Ó£}¶\Î\Zw\ˆæìæØqq5\≈≈¥i,k4å\Ê1õ î\0\ƒe\‘\Z\Ô5o\r\›\€\Îû\n\‘\⁄\Û\∆:vã-\”\œcu-πü|ë¢\√:\Ô1\∆\≈6ø\ zn≠%K\⁄Qëöîéã\√\ﬁ&\—¸Uo$˙.≠c¨AlíKîùQ±úÑ\‡\‚∏ˇ\0â\ﬁ8‘≠[X\—\Ùm\"\€W≥\”tˇ\0µ¯íi\€¨\»\Ò¢@¸µ¡}π\ÈX¸\‚Ö£\\∑ã¡~nü~\—π˛ÿ∂[©\ƒo6$ô<\◊]\≈]˚µw^\—|y¨x•¥ùE¥\”|K≤\›SS\Û§∂x¢ÚòØñø2∫sé∆µ£Fù:\◊m4Ñ\‰\‹v7g\Û$ü¸f9h\Ï2«∏Kâê ª\ÙÆ\‡\ÌΩ÷è\·;ø_M\˜\ﬁ\‘\'±y#Bã,R∏ç∞z≤ú\ı\ﬂ%p\‚m\Ìeméà¸$ãN¶s\ÎOÆQí~4\Â®\ÛN¸hw\ZZN}iè•\0^Ö<\…n\n=\Õqñ_4ªã\À9&\“\ı\Õ;Eøï`¥\Ò°j\"¥ûF  ±ëQ\…XååWen≠#\0™X\Û¿\È÷∏ø\Ÿ¡\„\ÀT\>é~\Ÿ<∑V∑\Zå\ˆ£|\Ze≠Ω\¬\Ã\≈\ŸxY\…P¢>é’µ);Xó$w-\Ú±S\√†\ı§\»\ıˇ\0\'•W\’5ç;Kë\Ê\‘5=;KB\ﬂ3_]$ ~,ET\–<Eg\‚´56+∂”∑Ç\ˆ\ÍÅg\Ô—Ä}ûçåVm[räû4¯Å°¸7\“©Æ\‹2bññëå\Õ6‹¨¥O\0u5ô\‡xä\ÛW\‘<9\„m.\œJ\Ò$\—\Íê6ö˚\ÌÆ-\\Ñp7\ÀXâ˛§É\\\«=K\«>=¯{\‡m\Ê;\rJ\ F\ÒïŒ†b\ﬁ÷ë\ƒ\ﬁT=x˘ü∑sZ~$\\ˆ~<\\r\È\Òoâßººπº\“f∫{®|\ﬂ+\Ïí\‹ÄD∏\·Cœ®ØJ4i{$õ\’\Ís\ RR\–\Ï<mÆ\ﬂŸÆó°hwkßk∫\ÎJ\"\‘d]…ßŸ¢á∏ª>¸Ö\\\˜ \n´\\Á¿∫7ÅõZ>éH4mD¡$kq#H\˜¢øùp\ƒ\ˆ}\…¿Î∂∞µèÖ∑\Zå4o\È>wä.mmg∞Ω”ºI©\»˛tr2∞í7`Q]Yq\˜pEuì\Îû+v\”¡ñ™¯¿ìP\Ò\n$h}í(ò‚≤úc\Zje≈∂\Ót∏\'8\«Zë_cnk\√v˙≈æí?\· Ω≥æ‘§ôßo\Ï\Î_*\ﬁ˛S?;˛˚\r\«“µ´Ä\‘\·\Ï˛¸9\Ïñ∂\«\√\⁄›ªãx\ıØ1B	õ-èj¿\–o<\·å\ﬁ7ü\œ\ﬁÉ:Nómâ\Ì≠ê+,≤HN \„÷Ωƒû\r\–|ib,ºA¢\ÿ\Îv®¨wë+f˚\≈XÇFk¿ˇ\0	¸5\‡ã\Î≠>\∆+≠B\Ì\„\Õ\›Õ¥*\Àq\ÌçÀç@\˜&ª)‘Ñb\‘ﬁ¨\Œ\\\…\Ÿû4¯\Ì¢¯OL“µ;d÷¥ãõ¯-o5®\’\÷\ \“by∏˝\Û\‡ïrx5\ÿxG\∆ZGçº8\ﬁ!\”nH\“a‹∑M®\"K\'N´0lydw\räá∆û≤¯ÅáØ=…∂\“\ıXuu∑àÅ\ÚGªjJ$Ø\Ãs\≈K\‡_Íö¥˙≠Áá¥ª\ÕNc∫KõãEwêû•≤$\˜‚°∫\r[Q{\«&π\‚\Õ\'Eü\‚\\∫\Ì\Â∆Öq®#\›A≤\“^\È`∂ñ1ç\¬GVW\«u`z\Z\Ëæ//à\„\÷~\Ÿxr\€NY\€\ƒRÉ}™\Ôkdaß‹Æ\Z4ò,\‹wS\ÈZ⁄øÇt\Õ{^áR\‘Z\ˆ\ˆ(dä\·4πn\ÿX˘\—\0\"î\¬¬Ñ8l.W⁄µØ¥®/\ı-6˙b\Ì.û\Ú\…\ng\Â\Û$å°s\Ó§˝\Í\’UÑ]\“V\œ\Òvüq‚üâWv˛ [¯sK\—\‘\ÈPZ[ù:¡\"níH$ífî\CZ\Í\ıùSO\Ò\◊«ø]X\œ%÷Ö6ô,n\Ú$é\⁄\Íh\Á¡é…óX\œ\ O›Ø[YB;B¸™%G±*j∂π•\ÿ¯óOZ≈çÆ≥eøx∑øÖfDÌê≠¿8\Ù5Kì∫],¨\‡~2Mq®\n\ÀJ“áâ5/\rkxèQ\”\‚êy±\€\€\ÓQ\Û\⁄A#b3\…\«∫{\ﬂE©Yò¸;ßÍö∂´xåñ\Èq¶\\ZEl\Õ¸s\À2™¢Øu-⁄∂\Ù]&\√√∂øg“¨mtªqåEeBæ\‹(\ÁÊØáf\„û[8\Á\Ú¨˝¥yTZ\ÿ\\≠\\\ÒM¿ZΩ\◊¡\€_Ñw\ﬁ∫\”ma∂K+çvõvµ\Ú\“6Kàê7ô\Ê1˛d\◊Q‚üÜzﬂå|Ø\Ëz\˜çµ\rb\ﬁ˙\“@ñ\\ÿ\€Ÿâ&\0ò\Ã\“ ,\√zåÅ\Î^ÜC.s\∆O˘¸\rræ ø\¬\Ôá\◊~!Ç\ƒjW©<\Z±¿fr\Ãﬂí£ü¢ì\ÿ”çiJ^\‚\‘9t’õ∫q(\˛ìÆ\Ë∞«®\Õk\Û\€\ﬂ\€$≠¶4,ß<\AU}[\¬\˜Z\È\„√ó\—¯f{)§ñ8≠\Ì\⁄OΩzO+∏ÿ≠ªπ†≤Gûi\“TUföf\nä\·I\'Ä	\‡z\”’à$Ç85\À);›õGcú’µØ¯k\√r\Í\ÿ>(ªãmæë{$∏?yí9\‰é¿=k\Ë~&\“<OM•_\≈u\Â\‡\À‹ö‹ûã\"T˚+AXØ\›\‚õ1≠\ƒ“àcéià/* ]\Ï;∞7@Oœ≠s\ÎE *kóöÖéì=∆ô§ÆΩ~ªvi\Ìy†ì˛\⁄:ê+&H|i©Z\Û\√˛V\È•§∫î\—ˇ\0\€Y\Z4?\˜\Õt4˙w¡˙Fµ¢i/ø\‚)<O$\Ã\Ìu%úv\ËäzFäá S[¸˙\”i\‹˙\“\0ß\”)VÄ3¸A\‚F\–ˇ\0≥¨\Ì,õX◊µ)å:VóπÇH\‡Â§ï\Ò˚∏P¸\Ã\„ì\–TZnáÄtõãΩgQé\Ô\'k\›KYøql≥\‹7\ﬁaø\0*\Ì\nã\Ëx©\ıi~ hßc\r\Î[áôç_\Ô\0\À\ÎL≥\èá\Ù˘£û\◊A\”`ù~\Ï\ÀhÜE\«L\»\Ÿc˘V\Òpq≥\'[‹∑¶j\¬˙\Ó¥\Îc=§jM§\”~\Ì.\‹.~PyOF\ËkÄ¯wØ¯wC˚5œÇµ\Î\Õn\Ú\‚K\ÕR\ˆ\Í\˜Oä9\Ódl\»¡ç\√6\’˚´\Ì^ôπ\Êm\ŒN\Ó1–û;zLT\œ\ﬁ$\“U,πl\r]\‹\‡¸o\‡\ﬂx≤˚B\‘bìD¥\ZXò>ì%\‘\Ï/Q±\—\ÁX\∆\Œ?ÖSoΩlIa\‚\rsZ\–oØ¨t\Ì\œMyL\Ò\«}\ˆ…Æë£\⁄\"UÖU\r\œ\Õ]>\ ]µ™\ƒI+[b}öΩ\Ÿ\¬h˛\Ò_É\„};A\÷\ÙG\–\„r\ˆV˙∂õ4≥ZÉ¸\‚ô7c±5¶<ˇ\0á~\ÒNΩw~u]We∆´sp\"\Òô<Ω±$q`®ªGìö\ÍvVGåt9<Q\‡\›cHç\’&º∑hQ•<~4{g9{\√\Â]\nû\—_D\>è§§éH\Ïñ9¶L+y¨2\Œ3\ﬂs¯UØ\nx?I\>û∂z5ä\⁄ˇ\0∑o\Û\‹Nˇ\0ﬂñNÆﬂê©¸>ö≥ÿÉ≠≠Ñwõ\ˆ˝üM\–∆É¶\\ƒ÷≠c)æk¢íC\≈\‘ ªVW˝\„ˇ\0\ƒ\“nfR	\Àµ∏o©¿¶”π\ı®\ÊoqÖ-%>§üL©ÄäLz(\‰é}iª©\‹˙\”h,u;y¶\‡‘ë«ªØóˇ\0Õá¸%\„\ƒÿôµe±m>2\Œ6$E∑1\‘\”5O\⁄k^(\Œø<\◊\ﬁh-+¿±â\ZAÇ$\ı\0\Ú1[;)\’JMu3ç\Ûn\Ô\\\‚¸5\\‘3\\\Àicq¶Ω√ô%M;Qπµà±\Ô\Â\«\"®¬∫\Õ>Ö&¥Ade\Ëû\r\–¸7pn4\Ì&\÷\⁄Ïúõ∂S,≈ΩDÆYá\ÂN\—|<∫ä¸UÆG;;\Î\ﬂb\ﬂå\Ÿ\‚\Ÿ\˜∑sª⁄µ˘\ı£üZ•9wÉ∑\ÍqOJäûÜñ\‡Kö~jß\ÓsR\Îû◊ºö∂µª¶\Íó:øø\Ÿ\Z˙\ﬁ8\ÊY°\À7ó$R)SÜbA\–\‰z\—U8Ü\ÊØÜuâ5?\ÍóI¸Kaoò¯©ê\ﬂUB\Ô\‡ü\√\ÌSPé˙\Û\¬vWÄm\Ûn7\»\œ\€2eàsèZÏíù∂öú£\\Ë+\"ï\Áá\ÙçKIìJ∫\—\Ù˚ç2Lf\Õ\ÌêEï]£\ÂÇ;k.\«\·oÉlln\Ï†\∆ôΩ\“\Ïï~\Œ§ß\ÃA\⁄}\≈tiR%\“}\¬»´°\ËzwÜ¥\Ë¨4´4\€˛\‰—Ñ_©\‰±5}r~\Ò&õ∏z\—F\ÚM\Z ç$$	0%	áléy\ÌSæ\„&Æ\÷,G÷üG¯‘âK}¿ë*D4\Œ}h§Å≤\ vcî¡e\r\˜∞{fíåJ|w\Ù©\0ß®)\–\“s\ÎGl\ˆ¶∂è\Ô\ZZ<é\œˇ\0Zùö`cMeyk\„ãmN\“0\÷\⁄|ñ∫éXYbeki\0\Óv¥®}ïk°Jäûºpx8\ÕSw^}i\Ò\”?\Zzw\ˆ©\0ß\—˛\œ\ÂIö\0~\r\'^Ü∞ºa\„[√¢õË¶ôµ}N2l´√∏±ˇ\0eCû\Ÿµ∑\˜d¿\?>ïM4Æ+ñ&∑ä˙\÷[iÉ<Fbx\˜`ï=Éáﬁ∏\€Ç\0≥¥[hº-j\ˆ\ r!ñi§MﬁªZCü\ƒ\◊io~î\Âc#fà\ QŸÖëã£¯¬æê>ó\·çNëzKù\nπ˙∞\\˛ï\—H\Ì#´≥ó~\€\…?Ü1Ä*\ZìÒ£ôΩ\∆Rá\√˙møàÆ\ı¯\Ìä\Í\◊VIßMpebL\€\’@\Ìó\‰’ü∞A-\ıï\Ï±˘óVbUÇF<BdPØÅ\ﬂpV\Ïz‘¥˙.\¬»ó\Ò†|\›9§èµR\”5\€\ryµT\”\ÓÖ\·\”o\‰\”/Ywb;ò¿gà\Ó˝\Â\Œ=G≠\0hØ\'Å\◊5\'\„YxõK∑\ÒU∑Ü§ªX\ıÀõ&‘í\‘#í\ˆ\…&\¬Â±ÄI\„µ≠J\Õnπ\ı¢3\◊\ÿd˝=h_õ°\œ\„\”÷∏≠K\‚ä\€|V\“<ë=Õ•Ã≥\Ÿ\‹\Î/ X°æKi\'\ ?à¨iµáP\‹\Z®\∆S¯A\Ÿnw~û˝=\Ë\ı¨ü¯áM\ñâ>´´\ÃaµB®à®^[âX\·bâG.‰ÉÖ\\ìä_\r¯Ç/h:§ó\÷6\˜J\Ã-µ3!\rÅπzé+7.-.k~4\ÓFI\‡ÉQ\Ê≥u≠_[\”\Ô-a\“|+Ωo$^d∑Ø¨\√fê∂\Ïl(—óqér8é\Ê∞˘≥éqH>núˇ\0ì˛\Ú5\„z\Õ\œ\ƒ|b∑\“t˝b\◊¡\Zì°,6W}\Ì,\Ú#4â≤!!!:òØS\Ò7ã4_\nGe&Ø®\€\È\–^J\—G%¡\n©Ñyÿì\¬z|\√÷∑ïFÀπ*j∆¥d1¿9?\Á¸\ÂSZC\ˆâ#V$F\«n\Â\Î˛zW\ﬂ4üx&\Óˇ\0¡\⁄\ıù÷≠v\„O\”#îïõ\Ìé|¥	0\‹2én\È\Õi|3\’\ıYuèx_\‘\"\‘\ı_\ÍQZI™\«n\"˚TRFí\∆ÃÉ\Ó∏^\n\ıß\Ïßk¥\»\œ¯\ˆø¸7k1in≠#∏∂ë‹ñê˘w/,OS¡Öd¸~ø≥mJµ3¡;\€_]5Õ¨rhôtã…£Yrß\ÁB˛\\ı\Ê÷æ\ÒØá\ıùoX\Òß¸ ∑í\Í◊ëh˛\n-€¥ó≠$^gí|\∆Ycc\Œ0\rF∫}ﬂà<3\‚\r\◊\¬\ﬁ\"ã∆ó\ﬁ7o[i\˜\÷rB´bvã-ÃÑDÉ\Ïø!∫\Ò^≠<4#Wù\»\Âî€ç¨z\◊\∆\Ì4k~&\ÄU\ˆi⁄é¥o5%\…Ã∂vQ¨éõá@≈ó˛˙µ\’¯\„\«\⁄?Åt\€-S^ü»¥æ\‘`∞Y≤#yWqvnÅB\ÚI\‡kñ\’tk\ﬂ4ø\Z\«e£\Èr\ÈâqeÅyz^I≠\ÁÕñKàë\—v¿ûã\Ì]5ûü©\Î\Zí\Í!ãM_!-2—ö\Ê8º\œ\ı\”\…$àªô˛\Ë\Óä\‚´iw\Íoù£Gys[\\[\›\≈\'‹íU’∏\œx©k\œ¸]\ßH\◊\Ï\Ìnt]+K\—|I¶\‹G}¶\Í6\ˆ±¿D—úÑê¢èêéEv\Z%˝Óß•Y\›j:i\—\Ô%]\”\ÿ\…:\‹õ\–:\EpJ\ÀcSOüZ*=\ı\'\„H•\È÷¢™∫ûª£\Ë~_\ˆÆ≥¶h˛g\‹˛–ºé\r\ÿ\Îç\‰föMΩ\0\—¸ipkòˇ\0Öô\‡πÅ\„-bΩΩ˙Oˇ\0¢\ÿ\‘˙é4}cQÇ\Œ¡u=BYk\\E§\‹\«oˇ\0jiïøT\·$µAtt˙\—G>¥s\ÎP\ÂYT§\‡uˇ\09ü\¬c\–◊à¯o\‚´ˇ\0\rI\„oC•\ﬁj\Z=¿Åû\ıû+ä\ŸìÅÑFqû\’\È:∑ã.4øâ\˘∂á\Ïz’ç\Ì\œ\⁄p|¡$8π\‹*\Ÿ“ît~§©#ß3%º&ieé\ﬁ ¶Iò*ÇH\0d\˜$Ä=»ßmmπ\⁄q\Îè\Û\È\\G\∆o!~\Î73.R\ŒkKßlû;àãìé\ÿ˝®˛&Mwˇ\0	ß¬´ãûnuªà¶\n~Y¢6è(=∞O\·UNã©≥§£π\ﬂ$o#2¢≥2\Båë\∆y¸©æû˝+\ ~?h˙Æø•¯/M\”uc¢%Œ∏\"ö\·\‰îB£\…}°Ñr!¡$\ÍiÉ¿~3\\⁄X\Ëø\¥\ı\Î§’í\Í$ô≠£éh\Ó7\r≤øõ0å≥!Æà\·SäìïàïFùí=à\ÿ\‹*+õyB1¿má´g°\Ì¿¸˙WÇ¸¯g¢ÆìÆYx≥R∫‘º[k©ŒówíxÇ\Èn \ﬂ+ç\“U=èC^ß\æ\·µ;\ÎHuâºEii®\…ek™K7õ\ˆòB°x˘\\Xn_CQW©¸.\ˆguv2m_R∏¯µ˝âi\"ù\Z\«D˚M\‚˘k∏\\K!\Ú\∆\›˝Æ∂∏/Üs>∑u\‚è±\ j⁄£˝ëΩm`4\Ó	V#˝\·\Î[z\«\ƒ\rG’ø±\‚k\Ìc[åìO\—\Ï\ﬁ\Â\Ì¡\Ëee\"\ÔëYTáΩhñ§¨tß!∂û”Ω\'Që”Æk˛\rk\Ï˚≠< ?\›\’5{h\Â\0ú\’\‹x\¬\„S\‘e\ÒZ\rïà⁄∂˙D≥\Õ1\Ù\’\‹(¨\‹\Z‹£¢ß\”9\ıß\÷`>ï)πß%\0ç\Ó}\ÚV¡L\€VvT~_µ7`Tßs\ÎG>¥rz\Z\·œ≠$Ä\Ì\ÈGN¶†∏∏Ü\÷8§∫ûH\Êï`ç\Áî y¢O,r0<—´\ÿ4&à◊äó≠5ïî\‡\‰\„ë\ﬂ\”\ı\r\Â\⁄X\ÿ\\\›\ 	Ü\÷ûmΩp©∏Å\ı¡†V\“\Â\¬v∂`˙Q¯\’7RáV\“t˝N—ò\⁄_Z\≈y\·\Û\‰M\√>¸äª\ˆy|±&\∆\Ú\Òù\€x«Æjíb\–P\Í\Ã\ \\\‰g8\œ\◊\Ú4π™Ë∂∞k:¥Qæºä+yòú™n∏\Ë	\ﬂ÷Ædz˚Uö2+õ\>µ´^x\—on\⁄\Í\\XYô\08R(N\œqñ<\◊B™ZD\n\'†\ıÆG\·k\Õ/\ƒW¡N\ÕG\ƒ˙ù\Ãg2âÑcºF*¥ìMêÂ≠é\’*l\‘J∂z\‡èP˝¸\È≤][Y¥us\rªO2\€\ƒ&ê)íV\ÂQs’è`95ïár\‹dqRf≥t}j\«^\“\„\‘4€µæ≥î\»a∏\›\ coΩ˛“∞˙Ç;U\Ô∆ß[ŸîµD\ÙΩsÉú\÷Vø\‚¯Q\÷u9æÕß\ÿ\¬\”\ ˚ª\0BÄ\0\˜ }HÆs¡?ˇ\0\·0˛»ö]i∂Z\ƒSœ•]}µn\ZWáâU¿U\Ú\ﬂåV±ß).e∞;\\\Ó\÷H£Gñ\‚]ë\"ógË™†dí{\09˙W\é\ƒ\›iZ∑ãß\‹.<U|⁄ö€æHÇ\ÚB†v˘H?Cö\À¯Ÿ≠x\ÀM\“ÕÆÖ¶\È7:V¥±\Ë˛t\◊%oE\≈¡(6˙¸†û;[∫\◊|Ej´l\ˆ\”\Ù\˜:{\È∂\È\ˆ\€\ÎS¿Fë\äB∞; ÉZ∫mR\Á3\ÊW±›≠Më\ÎU\ÍDÆR\À\˜ßDíåê7a\ÎP\«\\áãeóƒöÌóÇ\Ì§í\ﬁ\⁄kc®\ÎW1ú:\⁄d¨v\Í›å\ŒO`\r\\c\Ã¡ö\Z\ƒ\Ô¯É\\\ZFü}5ƒ≤\Ô[k£j\…gz\Ë2\À\ƒmêÄ	!I¿Ωg´Z_^\Í61\\,\◊:l\…\‹{q\Â\»\ÒáP—î˝\ı®¶\—-\ı/\ÏõX≠\“%±∫é\‚\“t\nct\«@Uà9\Îä\Ûç/\ƒ˙∆•\·x´\√\…ó¯íi\÷(ô˝°gjcÅê\‹ƒú‘ä\—SR¯H\Ê\◊S÷Ä%∂é[”øß\ı™:F•q5ŒØ˝•`\⁄eµù\„\≈\√8qulú}9-˘J\„5èiø\‰\“¸3\‡Ø4ø\⁄RCu{´i3n\Zmålí>\Ú2V\∆›áöŒó≈öŒπ\ˇ\0_\’\'ˇ\0âüàbël8D~DwóT\Îà\ﬂvi˚%v>cµ¯{\‚+ØxC\◊/°é\ﬁ\ÁPÄ‹ò\·R\0Vg\Ÿ¯`\Á\È]A\rç∂ìZ}äà\Ì-#[xTvD]†T˘Ærâ\Â\Î\«J\√\ÒW\ƒ¯!˛\ﬁ\’>\ƒ”©ïcé7ô\÷0peê %c¯è\ısX÷≠º7¢\ﬁ\Í\˜j\“¡eò#^ZW-µGvf\‡\…<\n\„<%\‚-G\¬\Èq?å|´\€\Í\Z¨¨⁄æ•m\ˆ\€qÅô\"A\ÚÅÄGS]4\Ë\Û\Í\ˆ&RiûîÆ¨±∫0ñ\0dëUÅ\„\Zñ\ﬂf\Â-ìs˚Æ¨3å∆º{\¬>#º\ø\¬kΩ9!\’\Ùˇ\0\r\ÎSiwY\Œ\˜\“·ªí1fç\níOd\'µt÷æ0\÷|C\Òb√∂7Ö,#π]W[πˇ\0Wuu∑	oΩ¿~§t´xy&\⁄\Ÿôû\’\ıΩw¬∂wæ$\”\‚\“uvöo2\ ›∑§j≤≤Ø=\Ú#⁄∫çîd©$r;ÉÉ˘+\Õ\Óæ \Îz\«¡ô|K\·\Ì.XºDd{9-\"âÆû\Œdª6\Û∫†bò$sÉ\\G\¬Maº7\Ò\∆\“j˙ﬂã£\\‰%ûã¶k\_\\\\\‹Âëö\Áiåù\‹}\–(XwR.¢{6∂:øåû$\”tˇ\0à\Ù\ÕN˙\÷\≈\'\Ûn ö\ÚUä$î^Y\Ã\Ã@ªäP?\Z\—\Ò\◊\«¯s˚4≠OK\ÒE\ı\Ê≠ì\È˙U\Ùw˘2\ÀFà\ƒo›¥\ÎñΩ`k˙N©\„/é_uªˇ\0∑¸#6÷öÖ≤Æ≠n≤4M\Â;ôgèëf8@\ÿ\…\‡WE\‚\Ì>-c\‚GÄ¸=oov\ˆ/7à\Ôí\›=±\¬U-‘Ä07N¸s»çΩ\ruJ4íÇõ\÷\∆~\ˆ∫Å†\ÍV^(≥K≠\"\Ó\rF\Œ]¿OMøyYz´\‡\Ú)˙n´e´≠\€X]¡z∂∑íX\‹	<x‹á\–\Ú8\˜\Ãxì·èá<]≠Z\Î7P]Y\Í\G,?l\“nö\ i£~Y$ë0\Œ	\ÓH5?Ç˛\Èæ\ÒàÆ\Ù-∫~ë´EdFè\Ê8ßÖdY%«ñëLd˚ä\Û\‰°k¶m©\◊QE;üZ\ƒb‘¥\»\È\Ù\0±˝\ÙÆ3\·\ÎCcÆ|B\“f6\jrx™\ÛS˛`-¨\Ò€¥2Ö\ÍG\ À∏qêGj\Ì?\Z≠}§Èö≥)\‘tª\rM\‘a^˙\Œ9à\˜\√¿\’\¬I&òcui\‚Ø\⁄>\rSIæ∑\‘l¥5•\ÕÕ¥ã*$\˜7\ÏQ7)#8G8ˇ\0eΩ\rzvkì\–\Ì¶±¯ô\„R\÷Z\Ÿ\ÍöY≤∏ÜA≤§WP¿`9ívlx5\’%kY≈¥£ÿàyòæ<\Ò•Ø√ü¯á\≈Ü6\Zm´M\n»ºI?	\n\\\ @«°\„Zûç\„¸\–5Ωq|=&ß\·\€»ºM<ìô.Ãí\»\∆Eî\„i;n6∞\œ6\œC^˚{ß\⁄jV\Õoek®[HUû∏RTle\»e=Aß^Cß\–_\⁄¡}\„l±\œtq\ËA\ÌE*Œí≤A(\Û4ùBk\Ô\r\ÍZmîzºöØ˝°.ö\Úàö\ÂL≈ΩæQ$fUu\ÏJ\“j>.\÷fâH\.øwy#*ë™\Õge@\ıÀâ‹∑\·]+y\ZByß/\Õ\˜ã∆£üK5q\ÚãMq,ê»±I\ˆyYG.7˘lWÜ¡\ÎèJñúãY-\n<w¬ø¸oi\„\Õ{Z◊æ \ﬁH≤\€[YZ]\Èñ\ˆ©-\‹Q\\yà\∫°R˝˙\◊k\‚oÜvû$≥\˝´ ∑1YÎ∂ö∂°>™Z\‚{\»\Ì\√mÄä¨\ÃCzä\Î\ˆS÷∫%^Rj]IQFTæ\–\Á\Ò\ÓΩ.â`˙\Ì\‰M⁄®Ä%\„´&\∆˝˙¸\Îë–ÉëSxs\√:GÉ\ÏEéá¶[\ÈvûcJcÑr\“6r\Ó\‰í\Õ\ÚÖ\œ@\ris\ÎEa)\ JÕé»ä\“\ﬁ=>\ﬁ-\–AmÑé(˙*é\’c\ÃfP§∂A\∆±=H¶füKôèKXMîÂéùK¯—∞¡)‘ú˙\”\„†B\Ï\Ù§ßs\Î@>µV˚C\”u+õ;´\›3Oæ∫¥\œŸ•º¥éfá?\›fRW\≠S\Ë\€`,ˇ\0j^®\¬\\»É˚™\‰~∏®˛g\‰πc\ÍI\«\‰EER\Û\ÎU\Õ\'ª\0¢ä*@\„u+¯_≈ö∂´\·\Ì.\ﬂ_\”\ı\√∑∂M®†û1≥\ÃVd*¿è\·\Õg¯ìK\Ò1\Ò\'Ö|e®Y\ƒWE∏ö¢h!Ø\'[{ò\ˆK3\»Q\ZFA⁄£ΩzHÕªO˚&∫Uf∫∫he’º7∞Mmyn∑V≥\∆cñÜ\Âu=çq7\ﬂ‚∑∫\–u#SΩmSCªYG≠\Í\\ZGF\—IU\\˝\∆ 1Æ\Û\Ôu§\ŸY¬§°±N)\ÓS\÷4õi∑\Zv©i°e+e\‚ò>\Î©´\nßc\·M+MºÜ\Ú8\Ô.\ÔaFä+ùSSπøx—ók*	\›\ƒc\È\Õllßl•\œ$¨ò\Ïå=k¡>\Ò%\“]\Î>\—\ıãÖ\n´&•a¡\˜\⁄6\Zã\‚&Ω?Ö˛xãP±Dä{ké\ŒPä≥9\Ú\„éôb95\—m¨\œh0¯´√∑zU\ƒ\“¿ì4n%èQë\—¿\√uúj{Àô\Ë.TV\Æà<+\·}HN~\√kL›ùá.\√\◊&∂!ç!£ä#ô\\$|≥\ÙV-‘ê?\nãO≥ö\’	∏\‘nµ)\‰9yØ\n+ˇ\0u(qc©îù˘ÜíC6∑≠=˙S©\‹˙\‘zå)˘¶R\–™O∆£ß-\0?üZ)?\Z(\Âf\Õ5\‘˙Tú˙\—œ≠UÅ\ÍG∞Q∑oNj]¢ç¢ò§+y%a\ZF•›ò\‡*ÅíI\Ï03^+§Õ•|a\Òäu_[\€\À\‡Ω+KS`\ÛóF≥YâH\Ú\—\„\nﬁ´ë\Î^ª\‚ç}o\¬zﬁïg,p^^X\œmo,π´<n†ùº\˜Æs\√_\n\Ï¥ˇ\0Ü≥xcYeøìP->¶\ˆ¨—§í∞U6X*™ÅÉ]te\npr{ôI;úVì\‚\ÔØ\¬\›«∑Zï§ZNümo%÷ë\ˆO2]F\–2G5ÃìC∞ÄG5\Î>,h\Ùø¯Ç\‰∫4V∫}\‹≈ôOÃ´éG\‘\’x.\€ƒöù¢Ü\”tã[ãfö\“\Ÿp\'∑á\Ó€ü\ˆOzõ«û><\–\Â\“Áæí\ \“\Ê\Í7æXWÊπ∑_ø=Éz\÷súd\Ôa§\“8üx\Íˇ\0\¬?	|)®\È\Ôáâ5D\” ¥±ä\‹eï\’\·\€\‘(PFjx>\◊¿\ÁD\Ò\rµ\Õ\Â\˜ç$\◊,\ÌìWöf/xíK∂x<ø∫!\€\Œ1ê+\”u.\√U˚1Ω”≠nV\ŒUö\Ÿ$à8Öïv©\\\’6\ûê˛(oΩä∂≤\—E‘å\ŒQe_∫˝™E\ÿYÉ´y\⁄o\∆ãª∑èT\“\Ô?¥\Ù\ˆ∫gÜ8#T0N##ós\Î\≈W¯ô©jí\È\ÿ˙é•e¶\⁄\Íoπ}£\∆\ÚV,f$¡›µπlt\Ô]UèÜ\Ït˝[U\‘\Ì†o\Ì\rI\’\Ó.f2F\n6™.xExéÊ™ØÑåw∑W6!÷¥Tºî\‹Ogb÷≠H\›Y|\ÿh=¡•	Df.Ωy}g\·Xº]ß¸@ê\È\ZvêeöKKKào\Êå\ﬁ\Âá\ ≈à}Hï§¸?\ÒVè\≤\'O\Ò§∂Zè\ˆkàa6v\–¬∑\ÓsHP∞ÿÆ\Ô^:\÷\Ï\ﬂ\Ïb\–d\—\Ù˘\\\⁄j\Z\ƒ\ZÜ¨⁄åç3\›*»≠*åmU›¥t\‚∂<Y\·m;\«\Z;È∫°ö(\⁄\‚+®\Ó,\‹	°ö)7$äYO#\–\kgYE$â\Â{úgÖ\ıØx{Kª\\ƒ>\Ò£´ç=.\Ù\◊\’$É¶D) ñ\Î~\Z5ï0ç\˜òt¨;ã\œxfÑ\˜~1\—∫ö\ƒ\∆;*˝Ø5˚°	\Ÿ3åÿÑ[†#≠zæì°&õu{w%\ı˛´®^ïzÑà\“R\€QUcE\ƒ¸´\\∂©}\Z\Èø¸\\$\›qaow•\€1?,Q\€\√\Ûîô¶,	\ˆ5º*√õbl\—\Ï\Ôu®\›|*\”`\‘4¶”Ç<ó\Û	Ñâs\ƒ\“N\ \Û\'C\Î^ñïã\·M$\Ë~–¥\∆%≥∞∑∂e\∆>eç¸à5±yµ%\Õ&\Õ\÷\∆/èº*|q\‡}g\√\Î|t\„®G\Zôô<\ƒ ∫∫ÜQ\…QúTZ?Ñ§èX≥\‘\ı7\”Q4ªvµ\”4}\–¡gfâ\Ââ\—R•5RJ<®M\\\Áº[\ﬂx´\·\ıîÉ1>´u}è\ˆ≠¨¶ï?#V\ÏDi\„\ﬂY5çå∑©\Ôπ\\üF1˘9qäõ]\– \Ò\ÿ./4\ÎΩ>ssi{¶»â<.Uëä≥´ôÇ\rI\·ø\ÿxN\ŒKm<\\3M3]Ouy1ö{âõÉ#\»y\Œ;iÃù;mnk-M¯\‘5-s=kù\’4]j\œ\ƒ\”\Î\ﬁõLí\‚\ˆ\∆+ª=_\ÕE\"6fç\„í Jüò\‰\Z\Ëi˘™åúA\ÍbE¢\Î\Z\√D<A´\€\€X\„\ÈörC\√˛ö\Ã\√\Õe\ˆå!£·øÖ\·_x@\–X§õMÄ£\Õ\»\≈\ﬁF\0\Û\…#≠oS™•RMXû^\‚Y\⁄\€i\Ò4V\÷\–A7\ÔB+˚sä\¬◊ºg´xB\◊√ñS>âmf\ˆmi-®\ﬂ\ˆ≤∫ºc\r\‘¢∫\Z]Çó3Ω\Ó;\"Va$å\‡m˘©)?\ZZÅú◊é\⁄˝Æ¸,m¸?u\‚8aæí\Ó[K?-\œ\Ë¢GêÄ#\Û>bOwC\—\ıª{]N\ÛQ\◊$_jjÃ≥%≠t¨/\Ó\‚µGÑ\Ó\Õ\˜´iˇ\0ª˛\ÎTøçk\Ì$ó*3I\›Üã\·q\·\Ë\ﬂN6\”[\ “π2Jf\r\Ê\»N1Ωôâ\œAS¯W@≤\>Å¶\Ë∫$mcß\ÿG\Â[Æ\Ì\Óº}\Ì«©-\…&Æ\”\Ès\ÀkÖóc\'¡û¥\?Ül4=9\Áí\⁄\◊\Ão2\Ób\Ú\ \Ô#<é\Ã;ñbk\ÌS*ÖY$ u¸	®ù¯\‘\Û;\ﬁ\‡;-\”qf\ıj˛\–g\Ú\”\ŒhDL|˛X}\€3Èπâ¸)Ÿ¢ó0%Zé™•NîÜMN\Á÷ôöw\„@á-KP‘©@JZO∆óüZ\0ìq€∑wÍÜ•\Õ1è¸h\Á÷ë)i~\—\ÎBR6\Â\∆UÜ·ëë\‘`\‰G\Ê)sL	ù5\ı•WUÜi§aP#K,ép±¢å≥1\Ï\0\‰ì\–R[\ÿ:\\öåx\Èå˚g•1%I#I\’\„uWVSê\ z{É\ÿ\÷~£\‚m+M◊¥=\‚\ËG™\Í\‚\‚[V]\∆DÖs#n(ì\ÈCOQ\\’¢ì=\Û\≈+≠É¡\Ù?\Á\ÿ‘≠F.\—N\Õ3\Ò¢òÊñôO¶π\ı©Uá≠Eœ≠˙\–πß~5>ÄO¶s\ÎOJ\0viﬂçGO†QI¯\“\Û\ÎU`\nó5LT)\0\OJ@\Ù\Ò•\Á÷öx\∆x\œó\Ò§1i˘¶~4o\·<⁄òûÉ\Ë\⁄=ipx\„ØJ•Æj\Ò¯o\√˙¶±qìA¶\€\…r\\∆¡wlM\ÿ\…\ı\‚í\◊@\“\≈›Ç§\Á÷®\È\Zü\ˆ\Êóa|±Ilóñ\Îq\‰H¿ïﬁô¡\˜Æ˛4H¢è~\‘óØ¿)˘¶QH\”\Èî˙\0w\Õ\Ë(¶n4P\À?çç74f¨\—Hî¥\0R\“S\Û@Ü\Ì¢ùö3@Ü\Ì£m;4P;\ÿmi\…EHÜ\Ì>îm©h\ŸN\‡&s^G®Hø\Æ¸O\·vëFØ©x¶}£\'\Á\≈\Õ\Ëú…∑Æ,y\Ù\È^ΩÉYM\‡˝o[¯Üm&\—\ı\ÿF\ÿ\Ô\Ÿ3\"çõx\0\Ì\‹Ä∆¥ß5\ƒn]∞∏æù\”\ÂFëä˚Tq\—JÄ˙v\œ\·\ÎYuπcêJ}N§R\Û\ÎMßs\ÎLc\È\ıˇ\0\ı™L–Ñ?üZ9\ı§¸h¸i\ÿ	íüœ≠Dü\≈R˛5 >üQ%Iö\0Zw\„L\‹=i\…@R≠ER\ÊÄ$Z|(\”H) å\;c9¸™:\·|i\‚^\Òuè\√\ÌCVé\¬\“xP\÷L≤≤	≠\—¢\‘\ 1\Â\rÑH\ÓH\‡é’≠:n£≤v;+[\”u\ÀyÆtùN\”V≥éC\‹XŒ≥FÆ\0%K) 8\Î»´\À\\è\√xD∫^´´Gf∫}¶±©\Àal±\Ï	j±\≈/b\…~z\ÔΩu€Å\Ës\∆\\:ô•4Ü?p\Èû\œ¯\ZU\Ô\Ì¡¨+_\€\\x\„W\∫\ƒ\Ò\‹\Èzl\Zú\˜í0*\»\Œ0\Õ\–`s\ÕU\œè-¸Y™J∫Nó©\\hi}õ\ƒ,\ÔuHA˘ä\œ\–\”t\ÂvÖsÆéßOªª¯GS¯g˘sU\‡ÆC‚óç$\ˇ\0Ü5à\Ù]cO≤\Ò%™\∆\Ú∞$6qœº†\Ás\·c@~\Û0$\—N®\ÌmGsªè”π\ÈO¡\Ù™\Í-4§’û-J\Ú4ç≠Z@ÖÆ!ßD\œRπFj\„Hâ$4±-\ƒ\Í\œFA∫E_ºTu w\«Jõ1\ËI\Í3\»\ÎR%e\È:ÂñΩ®kV6fG∫\—ní\“\Ë≤\‡	\Z4ò\ıX÷ú0¥ìSπÉ29;ó;á\‘`\‰v¡°≈≠ƒù\ˆ$\È◊äw>µªòVXôgâÇïí3πNÔªÇ=pq\ÎR~4ö≥Ö>ôR\Êê\«%ˇ\0¨£\Ò©mm\ﬁ\‚\‚5Tff\ËM5®/\√=F\ÔR‘æ$\œqs-\ƒp¯\¬˙\“\‹J¿¨qDë.\’\ˆ\»#\Í\rv˚O\\Wñ¸\‘\Ïº\'°¯¡u\›sH\“\Ê>3÷ùç\Â\Ïpn\Ã¸c{\n\Ù≠/V”µõ1wßj6Z≠ëb¢\‚\¬\Â&è#®‹§åäﬁ¥\'±1j[\}+\œ~/jZ^©´¯\'\·Œß\r\”\⁄¯∂˙3\ˆ`Ké\‚¨\‰¸™\ÓpXÒ≥ûï\Ë±˝\Í\Òß˝û_\∆º_\„]B\ˆw\“-Æóc`C?\Ÿ\’UC\ \“\nN9∂\¬{76\Íª$EK\Ú˚ß]\f˚w\√{9\Ô!s§\›\›h˛|\Û\0•`ù\—\‚y%Bë\Í5á\·Ø¯Jˇ\0\∆^/\ÒvØØiâ}k®>É§™\Õ\ÁM§c4q!$â\\∂XH>ï¡?ÖÖµ\r]<7•j\œ\‚Ê≥∏ªá\Ì(\ˆ´/ó&¸Æ\Ôn\ËG4ˇ\0Ü˛0\«Ä|m\·˝_T\“¸;≠\⁄\›^\À+ß\œ+õ©Y]A§R Ø]5cF.n:ô\≈\…\⁄\Ë∑\‚/å\–\ÍWöá|µ}¨\ÍYí]Jq\ˆBN\Îò\÷uDrX\Œ	Uˇ\0¯\€[óR“º\'y\·˝Z˛\ˆ\ﬁ9NßØ^Ojë[ƒ¨\‚ Öù<\Ú0Ly›é‘´™\¬7\ÒC\ƒZﬁ≠•ï´iV1\È˙í\ÿ\‹K>QóÕâ\ˆ¶\ËK1\ré¢∑4\Ôâ~\’&˚=ñ∂∑íç¨a≥∂∏ô\ÿ\Ù\»DR\Ÿ«≠aSŸ®r\¬?2\„v\Ó\Ÿ“•:öø+<0\Í;äì5\Áõ¢éò\œsÅK¯\—\‘\Á÷ñÄ	`\0\…=9\r\0‘âQ\«R\Û\Î@<sí9Øµ2™j\⁄[\Í\ˆ\ƒ∫æ±¢¥Ry©>ãx∂\Ú1\Ùl£Pö\∆\Ú}\‘f˙\“\…C∏HeX!\‹1Ü=÷πÀèAyów¨¯ìPƒ≥k∑1\Óˇ\0ycdS¯\Zã\¬¸=\‡iµ7\–4\ˆ\”_Q`\˜#\ÌSJáu\Û∂\’\Ÿ\“füœ≠ER\Û\Î@b\Î˛\÷\ıMb\”P—ºcq\·\…m°+-§\ˆë\›\È\Ú®/$n\Î\–w\ÕmSgÖ.≠e∑ïXfå§ëæv:≤\Ì#éE8…ßvS\œ¸\„¯£\ƒ,1xwR\§{ñ\Î\ƒ6ñw6±\‹c†µ\Û$?h\·\n{◊§/\Õ”ûq\«\◊Œº∑Q÷º5‡πó\√˙\'\≈4õ\€ÿûñ%\◊6\”5Å\ŒÓ¨Ñ\◊q\‡\›CW’º3¶\ﬁ\Î\⁄bËö¥\—fK2rc¿,\Ïn^JAÆúDb˝Â±úns∑û.\ÒäºA©¯{√∂wûµ≤ª{G\Òr•µ\‘b\‚C\"i\0¬±cÉﬁ´|E’æ ¯7¡2M¶¯øD\’u\Îô\·”≠\ZV7>\’!æ\÷ †{\‘v∑ó\ﬂ¨.¸!¶k6˙>°<íxÇ]SN{+\nªhº\‡Æeb†˛\Ô=kº÷¥[i3È∫ç¢^YLT¥3g\rª éUácZ{H”înïÑ\”gûx\œ¿˛j^)\÷\ÕÕÉ®æ\”\ıõ∏/\Ìnî˝\¨ è\Ào@πÆß\‚‘çˇ\0\n\ÁZ≤C˛ï´\Ùªu\ıíy?\Ã*±¸•>\◊\·◊Ü≠n`∏m1Ô¶∑ €≠˝\Ì\Õ\ÏQ∞\Ó±\Õ#/˝\ıU<dçÆ¸@\Né≠Ö∞\Û\ı\Î\—Ÿ∂(ä\‹\ﬂr3~á8\Œi\ˆ3∏∑±kKX\¬DcµâV$r0º/\’;çwE\”¯æ\Òâßü˙z\’m†ˇ\0\–\‹W7®|3\æπ\‚\ı\›_Gá]\‘\ÊEèv¨\∆\Ó\◊\—!ê\‹\◊E•\È\ˆö>Vôß\Ÿi©ˇ\0<\ÏmcÅ\Ò\’π_≥\ÎsMNwR¯≥•[j	a¢\È\Z\˜å\ıeD}Oi,π\Í^\Ò\¬ƒøâÆ∫6o/%g\”9£ÃíL\Ôr˝\Ì\« ˛\0\nZâ\Ú\Ù\Ó}h£üZ+0O¶S\Ë<øqE-\Ú¶hJe?5WŸß~5i\ \√÷ò•¡\Œ1\Œ3¯Ss\ÔYû(\Ò>\Œ≠¨M∏é\¬\⁄Kü\'8\ÛX.UI\Ìì“Ö´∞˙\\ÿé&«ó?8˘Tû}*6;IÇ=´ÉÉ\·Œü\‚Ω\rG\∆⁄ìj˙ÖÕππ˚]Ω„•æö•O\Àl\‰[	c\‘\Z\◊¯s©j\Z\œ\√\Ô\ﬁjR<⁄å\÷\˜Kåü\Óí=Oz\“q\ÂD¶t¥˙ç~^ºS£\5í`<©ê@ßV~ã¨i˙˝âæ“Øaæ¥4&\‚ê$_ºü\Ôåé£5wqÁéùh∂∂b%¡•¶#qû\’.yπ\ÈJ¿m¥u\ÈG¯ë¯é¢ãÄ™•é\0\…\ÈÅU4≠R\À[≥k≠>\‚;´UûKc$=ëæ\Ù©\Ó\Ôó¶\›\Í2|∞\€[Ω\ﬁ\Ê\·J¢\◊\Í\Â^{˚9\⁄\…o\û\ŸOÔ¶õQ∫ù\€9\…g¡˛G\Ú≠ï;\”u<\≈Õ≠èK¡\Ùßf£M‹üNøß¯è\ÃSøà/\Ò˘8\»\÷%ífü¯\‘U<8i\0#üaå\Á\ÚöWiï•\ÎGV\Òà¥\ÿ,\⁄8¥{à-ñ\ÏHπë\Ìƒå∫í2;df∂<∑å\·’î\Ù˘Ü+√æ\n\Íó_¥\À\◊oˇ\0dˇ\0h\ÍöΩ∆Ö§f\rIíW!ZYüñA\Z&@å\Î^µ†¯~\√\√62\€i±ŒêI&\Û\˜s\\o@\“1‚∑ØIS|∑\"2æ\Ê\«l\ˆ\Á\Ù\Œë¸©79\Î\\gã\ı\Ì^xgH\—.m\ÌëJjz∞xïö[F∫Ü\ﬁ8îg´d9ÔµΩ\rY‘æ&x{G\–<Q≠\\\›\\\r?\√\˜\Ú\Èwc\  \Àw\Z°0\«\Ír[ß<\Z~\∆vN\⁄0\ÁG\\µ,d\099\«\„\ÈU¥{®\ıã]6\‚\0B\ﬁC\\Á\“D\‹p\ZO\∆\Ì<?¨k h4hmµ\ÎK(\ÿIw}\røV\ÚáÕü†¨\’)=êsî¨6\Á<â\«\Û©30P§∂3åsåg?ó5\‚>5˝£<2|\·\…\Ù\œZ\ÈZñº\–}¢m>\‚;´Ω\"ã|˘˘%\Í\∆\Ïs\Õ7K‘Æ|I\vˇ\0¬∫Fµ©x´\ƒ\Züö\‚\‚;∆Ω[X§ü\ÃX.o@X\∆\"˘£u\‡WG\’gdﬁÇ\ˆä\ˆ=\«I2a#Ug,\«\0(\'\Ë$\—ã<1K¨ëJ°\„u9WS–É\‹}´\Õ|9\\Î\≈¡’µ\Ì\'K\–\‚É\Ïó6\ﬁ\Z∂íIÁâè\Õ\⁄g\∆\≈+\∆U	≠?É\÷\ﬂ\Ÿ\ﬁ\‘txgí\ˆ\√E\÷\ı\r&\∆iõ,m¢ì\‰]\›\ˆ\Âó=à\"≤ït\ÓRìguO¶≠K\\\≈Yßùq\n\‚u\ÛÖÆ5oâ_.u\À\ÔG\‚ù\¬K≠^Kk+ËÑ≤=\ƒ\≈aﬁ≤¨™àG\'#ä˙n\ÚfIGU*\’\Ã¯\·\ˆã\\◊Mº\”\ÙßäÀ¶ΩëÆ$\‹¡\œD\œ\˜Wµwa±¢•uv»í\Ê4º;\‚\Õ7\«Vf˚K∫7¨#û\ﬁh¸ªãy&Ö∞\»\ÿ\ÈêW\“\Á\÷\„\Ò\Áà\Ïµ#s>ï5Ω•ﬁë/íLQ(O.\Ê\"\‡a\\∑Ã™y\«56©\·}/V\’Sí;ã=]¢\Ú[Q”Æd∂∏u˛\Î≤$\Ï∏a\ÔZ\®ç\"L≥$j∏,yo≠s∑\›yfµß\ﬂ¯\€P\◊n≠t˚\Õc√∑~)í\rj\Œ\∆Xí\‚\Ê\÷\¬\⁄+X Q#†h\ﬁeôôT\Á≠w\ﬁ\ÒFô\‚\Î)ˇ\0≥ëΩõy7:e\Â£ZOj;ÖÄ`ß˚ÿ´:èk\·\Î)-≠wy2]\‹›±sñ/4≠+û=U}o\¬˙wàØ≠5§û\◊V¥Rñ˙•Ñ\∆®ê\ıP\„\Ô)˛\„Z⁄•eR*;XÑ¨o⁄©i6ÅëúWìx¡∑>$¯Ø\‚ˇ\0j≠mu\·˚çNX¥\€6bsufV\“9]6m!\Ÿ\€sk\“¸\'§ˇ\0b\ﬂG5∆µ¨jb92>\›pò_¯Hä:©\‡\Î\√>\n\—tΩBH_QÜ7í\ÓKu˘Zi$iùÅˇ\0yçM:æ\Œ.€±\…)nb_k\⁄eØ∆â\€^\‘\Ù˝.\”K\\Ï/ß6ßtê\'õ<\œ\ˆâr8çx\‰dz\÷\Z\È:\Ôã>.E\Ò\√cM\ZMæñ\⁄EÖ«à#π\«w\Ôgäò€±q\Õz\ŒÂï£ifhÜ#\Ûê9N˘RGL\ˆ4\Êvõ\Ô;3v\…?ê\»\0\nQ≠À±<ßüjüa≥\—¸W≠\€Õ©k:æ≥ππìQµæπ”æ\›t\"\ÃC…Çm™πP†u¡¨\œÕ¶¡\≠º\·-\ƒ\”jwZ<∂r]^ió6¢;©¢`\˜\\]*©!òû\rz¨++)*jF-\'˚\Îø\◊_Xì¯ï\≈»ñ«ã¡\Æm\Ô\‡œÑ\ı_\ﬁk´§›≠\ i∂pm= ±Ö§yA\ﬂ!iYS/\« wØq;sT˛\«\ﬂEw\‰\∆\◊qF\—Gp\ |\ƒB\ Ã†\Ù˘∂å’µ\ÕeV£≠kï:üLß\÷%è¨ˇ\0hû(\–o4ã\”pñwjæc\Ÿ\\4Ø\Õ¸,:VÖ/\„Mh\‡?É\ﬁ\æØ:Vùu\ˆ\ÌR\‚˝{%î\€\ƒ\Á\‰à3f!y-éMv∫mïæün∞YZ¡cl¨XAk∆πnßäïU§eU\À3}\–I˙Wa\Ò¡˙ß\ƒKüX\Í≠{\‚KQ!ñ\ﬁ8	É1ú:áeOv\Ô[9N•‹µ¥t;D•F*ÎÉùΩ*•ﬁ•i•¡\Á\ﬁ\›Ci\ıèÃû@ãπò\"ÆI\ÍXÖπ W)g\‚oE\Òi¥]R\“\Ãh:î7\'Jé¯¯Ñ\€,\Âî\˜H˙\‘∆ú§ÆI3≤é(≠aäxc∑Å	kµTgvE[˚U\∆\Ì\¬I	\Œ\ﬁX\ı\Ù\œ\'5KA\‘l¸D\—\…a{›≥N\–°-±ù£m=\»#\5\Êû\’<A\‚oiö‹ö∆°.ó®Xjw3\ÈM(˚•¢\›\«oßÖåÑ31$\Ú∆Æù9IIß±.IX\ıà¶ôX2H\·€®\Âø Gj∞∑WS\Ïá\ÌR∂z/ò\ÿ¸˙\◊!\„Mr\Œ\“\€O\˝\Õ∆ßew\‚©\Â\“ln4¢\–8ÖŸ•\…\Ë\'∂9≠\Ô\r\√6É¶\È\÷\◊\Zç∆•5úJ.u\Ãy≥0˚\“>8\Á\–VmIZ\ÔrÆ∫\r\—\ı\À\Èv⁄éóxöÜù0\ÃWJ[cÖ;OÆpj˛\“z◊ã¸\n\Ò≠‹ü	|\'ßÇºC}v[Ü†\ÌkSv`\»eú3G#÷ΩEömN \˜Z{\È\\ì‘∞…µ@\…%\„,\0\«zπ\“pó(îïÆr\ﬂ>\'\≈\\«M≥x\Ùãçv˛\‰=‘ñVßh∂±à˛˛\ÍC˝\’`@\ÕwÅ&\≈9\ﬂ\˜q\ﬂ\È^•¯ÉƒütØä˛.¥±\”\◊¡∫Üù&ü£_k\”K}:(ù^H#H\ÿ íB$\‡◊£¯^\„«ñ\ﬁ”∑\È~\Zé˛=62õµßeïc â¿†ú\Et\À\n¢íæ§s˘¢\ÒñØ\‚?ãB\—a\·=\':\Ó†\Ò\r∑7å\nGk®Wòéû[g°Æ\Á5\ƒ¸O/\·ÑôJº\”X¨∑R\Û\…r¡å\≈\œv«é¢ªOn\ı\ÕZ—ïí4[´Zw\„Pzé\ı*Vœ≠s\ÎG\„@¥QIO™∞u/>¥\’\Õ:ò>¥¥î˙LÑ˝ûWí%Hdê\Óy@w\˜\‹ —∏\Á9foV••\⁄})\\\‹\Ì\…lE˚£\Ë)¸˙\”W4\Í`\nµçÑ,\Ì¸i®¯†\\]À®\ﬂZEb\Ò\À 0\≈gç´\Í[ì[4U&\÷¿\nî˙)˚)u∏\r\⁄})\‘\Ó}h\Á÷ï¿9\ı•§\Á÷üRO¶fùö\0Z(¢Ä>Q\‹=h®≥Kæ™¿KIM\›K¯\—p$\Õs<ñ¯g\‚‘∏∂í\ˆ\Ùõñ1B¡I+u?Ä˛∫}kñ¯ö≠™xU4Æ<ãü]≈§,ù6\ƒˇ\0<\Á˛˝$É˛ZSºA=¥<˚\‡ç•\˜\ƒÖ:nô®Eü\·]>im.\ﬁg7\Z¥õÃª\ıé∑©»Ømi\‚é9\'ï¢∑∑Åw4íacâ=ÇÄz\Ù\∆\Ÿ[ØÑ˛$Ig\€]\ƒpy\ˆñ\Í0±_@äé£˝¯ ∞\ˆJì‚µç÷•\‡{ïµµû˙(n≠fΩ¥µ\À-¢ŒÜd@9$†\Ë+z÷©S»Ö¢$\–~)\Ëz˛°¥v⁄∂ï\r\¬≥\‘5k∂µæ\\eD23í:oÆ∫\÷H\Ó\ﬁ\‚\ﬁx\ÁÇe±∞eu=\në¡\‘W≠|B≥\Ònç®\ÈûY<I}¡$2Cijv\ÔûW]∏_\Ó©\ÕT\ã¯\”¡^\”|=Ü4…üFµ˚$:≥j´§\È|í4b&êÉëäèc\Õk1\‹\ƒ¯S\‚ª\Ô¸Bªä\Ÿe\—\Ó|B\ˆoò\¬€≤/\ÓÆ\nˇ\0u\ˆç\ƒq\Õzû°}i£\È∑zñ°q¶ùfÖÊπõ¢(8«π\'èz\·~\Ë	°¸-\—\ÊΩ\Ó∞?µ.•=\\\À\˜\‡~ïg\‚˛ñu\›/\√:G\ˆãi\ÍZ\Âº-\Â°+\“\'èô\—R¿wR\Âïn^Ç˚7}\„o[\Ë≤xπº3ßi˛∑_=≠\ı)^=M\·^≤?wü\Ó75\◊\Î^$\“¸5£çR\ˆÈ¢≥ë\„H\¬F^Y^Oπ\ZDπfn\0‚±†¯]£yvrxé)|[´/\»u/J\◊\Ãˇ\0Ï§ôT˙\0k7≈û\Ò_äæ\"Y\«m$zát{R\–\Í¯éKÉs*˛\Ò≠\„˛X¢ª|£¢JvZ\‹\€\ﬂZ\›]_Z\€]\√=ÕÉàÆ\·ä@\œn\Á8Y\09C¡\‡„°™æ\"\Ò^\\ˆß≠\Õ∫qKaˇ\0-•f\€_\#«π‚π¶\?¸\"zÖ∂≠\‡≠>\ŒR\–\ÿ\ﬁi3\Œ\—%\Ï;ôíO?k23∏\ıó\„\ÌC\≈w\Z~ãq?á#\“\Ùª\rj\ \Ú\ı\„ªmF`®˘$A\n(`$T∆úod\Z\ÿ\…\ÒwÜ\ıo\n¯_\≈:∂•´jzŒ©}\·k\Ô\ÌàZ\È\⁄\◊\Œimà\Ú£\∆\—ÂØù\ı\ÁﬁØ«£[^|7\øÉ%û\Í\rkYí\rJH¥˘\ Mgn\˜jñY\n˝¿Qåc8åWI™]]|CÜm&\∆\œP≤\\’\–d\‘\ıK\»\ﬁ\Ÿ\Ób\Ôonçøºå0+g√û—ºo-∂á•[ipMÃøgY\Ò\˜Alí\ÿ\˜¿ÆóYFü+\‹\ÕG[úπó\‡ˇ\0hZoà5-&\Í.5kôµMz\ÓxdÅT§v\Ê)e`\Ó\Ú≤ú@R{UÑ:óƒã\ÕoK—ºG{%Ö¶ün˙æ°\ˆ¶Y/.˛\–Œ∞A <ƒ´Ç\€N{[\¬\◊P\\µº2^@6\√r\ÒÜí1ªv\œ8˙äeæógo®]j0\€$zÖ\⁄E\≈\»\'Ãëc›¥s¿\∆\„P\Ò1ï>WJ\Âï\Ó_¨_\Zœ®Z¯ƒ≤i6\ÚO©ˇ\0f\\ãh\‚ù§1∞@†rNH\‡V\¬‘ä\≈z\n\·N∆ß3©xD\Ò/Ü\ÙK9bkI4\ÎHN\’-»º¥\Ÿ\ZeoºA‹é8\ÔP•Ø\ƒkmë\rc¬öíÅÉy}¶\‹C+VH§*O“∫\≈ ™®E?üZ\€\€I´KRyO<‘æ¯õ\\Òïóà.<sõ≠†≥π∑”¥∂åY<\‘(^sñ\Œ[≠¯3‡∂É\‡\ŸmÅΩ\‘|Aõ\Ã\ˆPjé¶7Ôù°Wsé\Ã\’\‹S\Î_≠’∑*v\'í\'3¶x}\'\√\ˆ∫/◊ìD∂_*+h~\œ\‚xè\Ì	óh^Õö\€–º5°xTFtMN\“d±¶≤∑X\Â#˝ßπ\…\ÓK\’\‰ß\÷\÷}\ \ÂCb∞≥Åwai˚ê\'\ıl1XÑJ6\∆:/\0Æ\0\ÕGN®sì›é»ë∑≤2\«q%ºååâ2æ,\Ù)ù\√#ﬁ©¯\√˙Ü4;-#Mâí\÷\÷%çZF˘ò\Ás\»«ª31\'\ÈV\È\ÙØ•á∞\Íó5\Z”™@ó\Ò£üZD•†ßQO†S\Ë§˛\n\0í⁄≠U[~öπ∏z\”RùHî¥Ä}Hï\ZTâ@ÆIK¯\‘Q‘â@-ß\”)\Ù}Q@˛(\“us¬öﬁó§ﬁ∂ó™^YI\rµ\ÍÆL27\›a\\O\√ˇ\0Ü6_\„‘µ\·Óè¢}±#Y.g\Ò3∏çP}‘ö[R¿ªr\ƒ\◊c\‚o\r¡\‚≠2;+õ\ÌJ\∆\›n#∫u\“\ÓD\r)_∫é\€:z\‚≥\Ó˛\Z¯SQ∫:éâπpø\Ú\◊^ûmMõ\Í.ñª®’å#\À#9E≥í\Ò/\ƒKoh\„Eµ\”$˝\˜ât[.-\Ôcª≤î5¿∏\ƒS°*Ã¢ÿÜ\0\Òºg≠wû\”5%\’â<K,R¯í\‚!nñ\ˆ|\€i6\ﬁ`ëm°˛\Ò\'cI/\ﬁm∏*\ˆ••\ŸjÎ¶≠›¨rÆùu\Â¢˝≈ÇTVUprF\„÷Æ\«\‘ÁßΩ++Zå:≥ä\.ô\‚ˇ\0x+H–≠¥}[\Ì=Y≠u≠H`ë∑≥˘¶áv\„∏\‰T^¯g™¯.=Al|rªµ+ñΩΩ\ZRÖïéYaÃü$j\Ó¯_\ˆ«≠_\’.5\Ô¯Üˇ\0G\–\ı#\·\Õ+Ií8µ\rf;h\ÓÊπ∫l?\Ÿ#IIUX‘É#gñ!z\‘^\Z\Òf•ã\‚H5´+çcX\Ω\”Z‹¶ãio£híX\'é0\Ô©ï\ÏV¥\Ê´∂≠®hÿö∑\√Hµoh˛%}wP‘ºK§\›\≈=•\Ó¢\À\‰\≈ìBêƒ®à≠BíMv\Õv∫m\Í\È\Gq~bu¥äW¬¥évç\«“∏≠?„ßÇ5XK\€\Í:ëh\√y\æá~dÅî!\‘Gï N{]¶ó®ZkZ]é£ap/,/≠„∏∑ôPÖë$ê\·π\œ5ÖIT”ú®•–É\√>∂\èÖ\Ùm\n\“Vö\◊L≤ä\Œ7aÇ˚íGl’≠KOÉX\“\Ô\Ù˚≠\Ê\⁄\ˆ\⁄[iLMµ∂:\Ì`lv5f3ø\Ó2=Íèá|A¶x™\Ó\Ú£$\ˆ7\÷\Ê9bí`q‹£Äp›â\ÎX^WπVHw¸#∫j\Ë6ö\ÿ\∆tkh°Ç\€OlòÑq}\ƒ \ıæµ¶≤ê\ \À¡\È\\§?º=átù_R\‘\"\—a\’\Ôd”¨\Ì\Ô§S,\”$\ÔP™s¥ë\Î]4\◊i\Ò\\\‹^≥\€ZD\Û\\\„¯cAí}∏¶\‘\Ôv\Z¸û\”a\÷\Ó5=.\˜V\˝\‰\Úy∑£ﬁî∂ñC\À<ñ\Úâõ?\ÏÅZ2\È\◊\Ò\Ÿ\\Iu\„Mil\’w\Ã\Û≈ßD°så¥´j•Fx\Ê∏ˇ\0Ç\ﬁ$\Òè\ÙçG\≈z∫Kk§kWkq†\Ÿ\\*Ç\€f\¬\Ù\‹H`OQ[±À•¸@:\‹w\÷	{\·ç&\Í\ÁNkk°ò\Ô\Ô`\‚F1\Á\ÊH\B\Ó˚\Õ\«Z\⁄\ÚÊ¥àZ#¶∑TÜ\÷(ïÃ±*\rÖ§iw©>§Véµ\Ê~¯É\·è¸\'\\'\ˆ÷øgg+\Ë÷®êª3 É\ÀP\Œ\…YTr\Ì¿ØJ≤ö\ﬁ˙\Œ+ªKãk\ÀYFcû	ï\—«®`pk	BQ{öd¸˙\“%\˜ß-MÜ\Í3H3\0I\Ë)Å7>¥Q¥\Á˛îù\ÒûiÄ¥˙e?œ•Hßs\ÎM§\‹sé\ÙÇ\„ø\ZZb\Ò÷§\⁄\ﬁˇ\0ïP?À°T»•în©’ÑµöOπ∑˚™MtCN\0ûú\‘ˇ\0\Ÿ\◊?\Û\∆O˚\‡\’\ÌON\”o\ım:¿z\ﬁ\ﬂE˛ÑE≤\Ï+¢~\Ÿ\Ì\ÎEs\◊<gú\ﬁ4\\Ò_H5X\'o˚\Ê74ñø¥+\Ë¸\ÀuMF?\Ôi˙°8¸\÷3U\Ïß\ÿ\\\»\Ëá*H\‰ß“ü\\Uø\≈[k\ÕN\Ó\Ÿ¸„∏≠a\€\Â_K\·\…\ˆKûªW\Ôè\ƒVΩøç¨Æ?\‘¯{\≈\“\‹\·ˇ\0\—\Â(t¶∫tm\Ù\Î\≈>:\√\Ôâ¶\Òó~gÜuØEòçµî∑Gòz\‚)∑#¨Ä}Õ¶ä\0˘3p\ı°zäØæïjÆUã;\Õ.\„\ÈPoßn©o°ñ6\ÿÃâ)Fﬁ•\«!∞À∏z¨EGö}1îµ\Ì\Àƒöo\ÿ\Ô¶\ŸV\Ê\‡;fÇe;ï\„n\Ã>\È\œT\⁄L\Zçä\À\ˆ˝W˚ZV8G˚\"[Ö_B\ÛS\“\Ô¢\ÏV‘ü\Ì2ïiî\‡Å˘j;\Õœ¶_\«\œ#\€Jâ\Î∏\∆\‡~¶Öa\ÈNV*¸P\Z\Ïe”æ¯N\ \Êkum£Y\√<rREÖ\ËAZz∂óeÆ\Èw\Zn•g˝ç¿Uñ\ﬁe	≈ª9v\"ß\ﬂO\‹?º*∫\‹F.â\‡}\√\Ú˘∂öhyï≤óì\…w\"Tiùà¸Eo/\‹\‘ç9X—æ\‰\ËHµ,l\ r¨\Ì\Í\Í\rEëNœΩ-∂.˙X{6\‚~\è∫_†¸6é}h\Á÷ñ\Ó\Ïñ?4\Ï\‘T˙@KN\ﬁiô\˜•†	sO\Á÷¢©y\ı†üLß\–âRTç;q\Î\Œ(Zu34\‰†	)\Ùƒß\–©\ÈL©®üLZzP\ÛN\ÕEO\ÊÄE\◊c@µ˘€ö¥ïücpì}‹äæîcüZ*∂\Â\Ê•JrJë)´N¸hH\ÍD®\–‘ô\˜†b\”\Èî¸\–≥KLßfÄä(°\Í1\‹˙\”Z˛\€Kå\‹\ﬁJ\ÒZDT\…\Â\¬_\0∂	\nπ=)\‹˙”ïö3êy\∆‹Æ0~†\”N\¬zü>¸	\Ò\≈\ˆ´\‚M~\Ê\«N\÷|O\r\Ú+9≥êCß-\„\›\‹\À93Àà—ÑR@ò#ev\ﬁ\r’ºGa}\‚õØkwæ \‘5Fπ∫ô&≥∑≤5XaHdíQ!Eä5\√cë^ñ\ÃÃ°N»çG\»˝\Ê íh\⁄˛ˇ\0ùwOv¢e\À\Êr\ﬁ*≥\Ò,ˇ\0\n¸u\r∑î|S´\€^L∞i\Û3\"\ \Ò,QƒÆ\ 7ïEy\‡ö£.±™j˛\Z∑\\ÁÇ4\›[\√7b\¬h\ıùgL\Ú-¥òUP∏yBÇÅW+ﬁª®\˜+|ßm+ne\⁄¿ë\ı¨Ug\’\\æSãº\Ø\ƒàm¸üâ\\≈5º\Ò\‹\Ïè\√Iw,>\Ú\\2\ÃYÅˇ\0f∫ç=^;É}≠.éu5ÿ©.ó´ò\«ggb\Ã\ﬁ¯´¯4˙áUæÉ±\≈hˇ\0¸£\ÿj∂©•5\ﬂ\ˆßò∑7W≤ôÆù\Ÿas˛ß.A å‘û6\“`”æ\Î1xã]’µ˝6;cK9ëc\ƒj\∆\›I]èéMvãöz≥Bsm\‰îê€∑n¶8™U¶ùÿπQÉ\˚Mπ\\ÔÄ¸\'¶\œïua•Y¡,l0\÷1\Í¡´˛\–lº\'ßµûñ≠R\\Ov\ÊCº¥≥;ªì¯ö\–;ô∑1…•¨úõìë],E•\È∂\Z,3≈¶\Èö~ù\√t\—Y\⁄Gs7˚h™°ø0*µüÜt\r2\Òo,|9¢\ÿ\ﬁ\„h∫¥\“\‡Üo˚¯™¸´Fù∂éi5f¡h>§¸j:};\0\Í\Ê|g\ÒO\¬ˇ\0\Ô\Ï4\›wQπMOR]÷∫eïç\≈\‘\”/†TR3\ÙÆõüZ±o®\\Y€¥0\œ,q∑\F˚\Úc\4Ä\‰¢\Ò\∏mñ\ﬁ\r\Òsß˝4\” Ö?)fCW#\Ò±3\"ØÇuH£nØ6°ß†ˇ\0æV\·çm±f˚≈è\„RFG#÷µ\Êè\Úëo2íj:ª¶\·†\€!ˇ\0ßçl\'˛Åo%#^k\Ì\Ó4ù\’ˇ\0ÈÆ´<\ﬂ\ \Ÿ*\ˆ\Ã\ÙßsÄs¡\È\ÔIM>Ör˘ú\Ôì\„I§\‹uo\rYØ§z-\Ã\ﬂ\Œ\Ú:û\ﬂI\Òó7^*∂dˇ\0ûvz\n\«˙\…q-mòA\ÈRv\'∞\ÎK\⁄y\n\≈±\ﬁ\˜\Ò6™ø\ı\∆\ﬁ¡\Ù+V¶6õw/¸\Ã:\Á¸X!ˇ\0\—q%[©\Ã\ƒì¡\«◊•\“W∞r#oAp≈Æ5Ø\\n\Íß\ƒà?\ÚâPø\√\Œ\Í\˜\˜◊è\Èw¨\ﬂ\Œ?\Ò˘k¶\Á¶»§¸j˘\Â\‹9QëÅ¸1O\Ë\Ûˇ\0\◊∆üˇ\0˙0\Zπk†iv+∂\◊H”≠G˝0≥ä?˝VÄR¿ê2)\€>\\\ˆ\ı¸q¸\Í}§ªá*#Öö\◊˛=ø\—ˇ\0\‹˘ï8\Õ3*í\ÓO\\\Ó\„\Ú¿§<rx˛ùkOÖ\Òê\\Ïvm\Á1u!p\“/¥ä3Ü\Ó\È?Ωˇ\0è\Zå\Âæ\Û¯öíçïõª,^ø67sR%Fï%@¢ì4P\«˚á≠™*~h5±&}\È˛eAövh$óy©7\‘\˜•\ﬂ@nßf°Vß\Ó¥/ôNW®íñÇlX\Õ\Ã—∫™\‚%\ﬁi\€\Í/∆óüZ.%©2\…\ÔRnµVùº\’\\eØ3\ﬂ\ı•\›U7öì}MÄ≥üz~\·\ÎUw\Zöã.jO∆†©sR“ß¸j∫T\…@ß\‘çIö\0r\‘vw\rsn≤5ºñ\«˚íéú\nvjO∆Ä$©£CRgﬁÄ$\ÕI¯\‘.h\Ù\Ô2ô¯–î6i\…Q\”˙\Ù\ÊÄMíX\Ï\ÌeªπöK±\Ê\\\‹\»4\»\»\À$0˘\“*ì¥{◊Ü\Í\ﬂº!\‚mrˇ\0R\◊ O›≠©>\ªBL-h\”Ö\√_(I<å≠ñ8X\»=\rt“¢\Í]\Ù\"R±\ÓqHìC\ƒSEuk\"\ÓI≠\‹:0\Œ2pFhz\·æ¯/[û©©\…s˝á°\Ëw ≥/Ö\ÙH\‰ö+[úa§I[\n§Ø$*êOJ\ÓsY\Œ\n2≤e\«]\»\Ù¯|π{VÇUHX,ò\ÈWR≤\’\"SsN¸h$íüL\Õ;4\„\È\ÈL\Á÷üö‰üç-34˛}h˙(\Õ\0˙(•¸hy\ı•§ß\–O¢ùœ≠\06üIO\Õ\0˙e;4\0˙)?\ZZ\0~iŸ®©\ıVD•¶\“˛4X	3NZä•\‹=jÆ˘\ı•\‹=)øç-;\0¸\÷~Ω\‚;?\√\˜\ˆzµ\⁄HÃ£˚\'Jö˘êõñ58¸j\ÌMn\ÂX¯F\Í(∞ÆfY¯∑LæPSO\Òd,æΩ-˘ytö/åº=\‚K\ÕF\œG\‘\Õ\Ì\Óõ\'ïyX\›[Inˇ\0›ê\Às\Ì\\EÁä¢’µ{ãO\ÍzÁÖ≠¢ºòC§\√mqoc,#Ñyo\—yºv&+∑\¸˙\È±[¯n\ÎI}:˘a\—n!xPéø,Mú˚±≠\Â(\Ëµ3M‹ø©Z\È3\ﬂ\Í7ê\È\⁄}∞\›=\’ÀÄà	¿9<H™v>6\Ê≠©Aac¨˘⁄Ö\ƒm,\Õisn“¢\„sDeâÅëí3å\’À´]V\Õ\Ï\Ôa[õ)H\Û!êp\Í\ıÆ$jS¯w\\Ω◊ºaa©œ©\Ã\Ô\Zùù´^YYŸÜ>T1$%\ﬁ=\€F\Êaﬁ≤ç5(∑}Qm¥z\Â\Îé+ç{\Ôà:ˇ\0â5ª0h\ﬁ\Z±±ìeà\‘t\È\Ó\Õ\Ú˘jfI\—7\˜I\”iZÖéªf/t\€\Î}B\”≤¨°[—∂ìÉ\\ØåºUcq™I\‡\ÛØiæ\ZYm∑Íöûß}\r°Kwˇ\0ñ6¶F•o\‚a\˜;‚Æä\◊T)\ﬁ\r\Ò¯≥¬∫VØ=≤\ÿ\œ}\0yaF\‹t%O°ª~tàã¿<\n\‚\‚WÅ|1¶¡a•jqjPZ\ƒ\"ÉOΩºöôU¿¶\0\Í>§\◊ko(çÑ\»m ∞¡_Ø•DΩ◊©]F\À\‚Sk\⁄\ı÷ë\·_À¨Oo˘uçe\€O”ëXê•c\Õ($85\Áûì\‚Œ≠\Ò2=ƒæ \‘4àçº\◊O&ñB\€$hvF\"Fâ‘∂8h\Û^É£\›7Ä\'∑\\Ó°∆ìqq\Â\Ë˙†¿Qñb∂≥z8,v\˜ªf≠x£C\’Ωßk\⁄ñ3jV∂≤X\Àc~\ÚC≥£Ç≤\"1Fµ\Ë”ú)\ﬁ	-QÉMª\‹<9´kñ:\Ò\\Ôàd¥Ωù\·7ñ:µúf$ªâpd\Îä˚Ωr*\r\’~#xüZ∏µ\Ë∞»ºÄ#\‰ˇ\0{è≠Sæ‘µ\€©<W\‚?L–≠¥[)£±±µækŸÆ\Ó¶*tÜ(¿\Â@\€\Î[ü¸?.Å\·ª+ó\ﬂ~¿\Õw)˛9üíﬂùcQr\≈À∏\÷\ÁDù©˝zs\\\rèâº{Æ˘\ÛXh>\Z\”t\ıô\„Ç=b\ˆ\Ë\›Ã™\ÿ\ÛG\’\»\Ë;÷Ωé≥\„(\ﬂ\ZèÑ4ªîˇ\0û∫N∫ˇ\0øsƒã\\éõ]Myé°*Zâ*D¨\n$˘h§¡¢Ä>6¸iªçá≠á≠ó¯‘ô®wZw\„@â)\ \√÷¢\ﬂE\0O¯”ñ£\Õ;\Ò†	ëá≠;\Ò®R§\Õ\0?}?5:Ç	Vùüzè4PBO∆óüZã\ÕO;\ ﬁæn\›˚3\Ûm\Œ3èL\˜©?\Z´Ä¥¯ÈüçJî¿ë*L\‘IOJ\0óüZ}G¯‘ô®O∆§é°\ÕHî&i¸˙\‘Y©?\Z´\0µ.j*}H\Û\ÎOCL¸h\Ìûﬁ¥0\'¸jF˘x<Œ£*\ *@=8¨\r?[\‘\·\ÒÊß†\Íp[ã+ãdø\—.\‚\‡Ã´\≈\ƒ-ü˘isü\Ó\Û“≠E\ \ˆù58|\›j≠\’Â∂ócu{u\rïît\◊7\„åz≥\0˙\‘\⁄&£ßk∞\⁄_i\˜ê\Í∫t§™\Õk\"»§é†$(\Â\Ï+ñ*2F3ülg?ó4\Ÿ.V\÷9\'x\Á∏H’ù°∑å≥æ:ík\ <9\‚Øi∫≈¶°Æk6˙æè6†4ùN+V”û\⁄\¬\ÍGTá\Ï\Ìn|\–C∫+,Äs\‘W¨\∆|πós\Ù≠jQtùô1ó2\–\Ê|\‚\À\ÔxGX∫∏“Üâ¨X]_i\ÛX˘\¬}ì\¬p6∫\yØ/¯r∂>\‘>jd\'\ˆn±\·[\È§P#¥∫0∑íG<óß_ºÉΩv˛	∏\ÒÖ\Ìu\Ì6\ﬂ\¬7ö±\◊5¯Ø/.!∑\”eI¶\ﬂå\‡≥\‡\n\"^qg˚7¯û\◊\\\”5Kçk√∫\‘iìPª–Ø\Ì\'\ZuΩ¡\r\Â$qÜ>dQ¥å@\'\Z\ı∞¸ëåî\ÂkòJ\˜L˙!w2â∑¨\—H2ìDw+PGù\\\œ\√\Ô[|?\˚\Èñ\Ú≠\√Iw-\ÙÜ8E$ùV\ﬁ5\'ÀàvPIÆï˚◊â$£&t≠J\ˆ≤âµ)NWï\Ó+]\Z≤\Ì|\ÁeP	;YªëZi¸5&ßf£JttKO¶s\ÎOJjKœ≠üç/>¥\0¯\ÍO∆£J}ß\”9\ı•Z\0ì4¥\ }\0:üög>¥Pπß˛5Hî\0º˙\—G>¥P∏\”\Èî˙\0};üZb”ø\ZkPÒß°®“ùTô•¶Tº˙\–œ≠-\'>¥\Ù†“•%*UÄ∏4S\„¶\‘\‹E\ry5\Îã8¢\–5´}\n\‰…ôo\'∞7é\"\ÙA\Ê \ÎX˙OÄmm|Pæ(\’5+\ﬂxü\Ï\Ê\◊˚J\Ì\"Ä$g∞äE\«˚¡\Õu4ª\“|º®I+‹ñ\Í\‡{\÷B\ﬁ¯\¬ ¿i\ﬁ\rú\Ô]z\Ù)ÖEïjQDg\ S\‘\Ê£\æ•}\„ãOjw:]ç≈ºB\÷˙¥à\˜a˚\‹\œ#î\√nk≠é˙\‚˝‘ÆÉ˚\Ï>_N\Ê°\Á÷é}i §§\Ó+\"fº∏ì\ÔJ\Õ˛\”9\œÈä£©i\Ú\ÍâãUø\“gÜ]\È5ãGª\ËVUu\"¨\Ì>î\ÏJ9ò\Ã;\œ\⁄j\–\√≥´kæ Ç9\“\Â-u\ÂKeërì\r≤Bçè\ˆ’´{JPõ∫sN¡ß)9n+t9/y\Z\˜ä<7\·˘zF\«YºL\‰0è\˜p©\ˆ/\ÛWX¨Y∑ÉXZnâåµ˝J\Ê;Y-.\„ÇFéf.#A\»(…Ö˘πÆâc\ÌNrVItV∑\Zä¡Ö\›%\Ï\Ûé\ıì\Û(U©Rô◊•Hï ;˚\‘Qπ=\Ë†ã®§¸h¸h,\\”º éï(l‘ãP°©3\Ô@fùöäüö\0ïM>°\Õ=MM≠;\Ò®\ÈŸ†ë\Ù¸\”9\ı¢Ämb˚c]\Ï>wñ±\Ô\œ;wn\∆*zL—ö\0rT\ \√÷°¸i\’`Lï%Aæ•J\0ì4˙ã5\'\„J¿IJÜ¢éúï >¶®j^ùj¿v\·å\Ó©#\Ô˘\’Z\Í\Ê\√Fæº≤\”e\’/-°i¢±ÜPèp√¢Ü=˝©<9ØY¯ßC∞’¥\Ág≥æO1VAÜçï∂ºm\Ë\ \‹<É¡•m.öW9≠xä\Ú˚\∆V>\—.\·”µKõ\‘g\‘%Dy°áyUX\"cµ•g>ÄWG¯\◊\„çN\ÒOé|!•\Î6˙éõsß\Í•!ñ2	∏å[0˘Å§G\Á0€ë\‘\÷\Ù9\\Ω\‚%©7\ˆV£\‡ˇ\0xuW_\÷5m/Xkãªmj\Ë\‹ù`3\≈<|\rºD\„i˛\ıY¯î≤i˙>ï\‚8üdæ\‘cΩõ˝ªF˝\Õ\“˝6H˛\0Oj\‰|C°I\\Á\ƒ_\ı}_Xæ\\‚\Îb\¬}/Rªkò\‡í\Í9 I\÷F¿S ^{ê+‘µ\r2\r^\¬\˜Jª\√[\ﬁ\ƒ\ˆ\”g¶\÷]§\÷\ı-\Õ∂Ö\’4\€=R\Œ\ÛOΩÇ;\€KÑ1O\Ë¿\Ù˛bπ/\ÎZwÉ˛%x˛kã´m+Cµ∑\“\ı+è7\√í,\‚GP8%Ñk\Ú¨Eh|7ºö˚¿∫^3>£gi\◊h~\û›ånO©!C}kZ\„√∫=\Êµo¨O§i\˜\Z¥1¨q_\œlíMÆ\‚°IKpk(MBN/`îyë\Ê~?á\Ùˇ\0?SΩ∏\Z∫´\ÎV>öíG p-\Â∫~¨\Î\Z\∆\ﬁWEeÊΩè\Ô6\„¡®\∆O\Ã\«&ü¯\‘’´*\“\Êê\“Ih;%ÇÇpæô•¶”´!J¯®ZW®)h2%øZºå}+;q\Û+N2=iôjE®©\ÙKO®ˇ\0\Z]∆ÄZ\Êù¯\‘yß-UÜMN\‹=jcN¢\√\'œΩçGöç\∆G≠>†Jìq\Ù¢¿I¯\“\”i\‹˙‘Ä¸”≥QS\ËO∆óôöUz\0u?5\„K@Rfôº\“\’Z¿Kœ≠?5\„N¶™^}iôß~4\0¥¸\”9\ı£üZ\0ï:Å‹ú\n\'°\Õr^6\’5\€+Ø\r¶ç≠\€hVóSE®\›^i\ÎyåE∫<åÆ—ªçﬁµn;\≈+#¥û0≥\⁄\›~àc\Ûô´x\¬\ÎVMŒâHM>±˛ÀÆˇ\0\–\€\'¸Fµ\Ã\Zõ\Ïz\«\¯\√Sá˛∏\È∫Xˇ\0–¨⁄èføò/\‰j\—Y)c´è˘úµ\”\Ùµ\“\”ˇ\0A≥è¢\›\Õ˛≥\≈^$ˇ\0∂w6\Îˇ\0†¿*yc¸√πÆ9\È\Õ\Ã^x\"K\ﬂ\ıæ.\ÒÅˇ\0ÆZ\Ï±ˇ\0\Ë8®£¯{¨\Ò\'å§˙¯¶¸\Ëä=úò5;â\ﬂ\Ó´7\–fù\ˆYOEc¯\Z\„ø\·X\Ëíˇ\0\«\≈œâ.øÎ∑äµCˇ\0∑ü\®¸\"z\Ÿjß˛\ÊMQøù\Õîˇ\0õ\ßt∂W≠º¨=êöñ=\Ù\Ùµúˇ\0\€6ˇ\0\n\‚-~xJ\–\Â4@\Ìˇ\0O7∑Wˇ\0\"\ ’¢\ﬁ\ì}\Ô	h\◊]6?\Ù44˘a\‹5:¡°\ﬂ˘t∏O¨L?•W∏á\Ï*Z\‚Xmw∏ùP~¶πô<	\·	?\ÊH\Ø˛,ø¯\ÕYOxz1è¯F\Ù5Q\‘&ìl3ˇ\0éR˝ﬂò\ı\'∏\ÒgÜ¨\∆n|W\·˚Aˇ\0MµãT˛oT[\‚wÇ#\‰¯\Û¬¨\Ÿ\◊md˛OZ+•i´ÚÆìß\∆?ÿ¥å\Ï¥¯\Ï\Ìmü\˜V∂\Òˇ\0π\‘Qj^bJH¬õ\„Ä≠\ç\„\"w=\ﬁ\„\œ?˘\rMC\‚oäë\ÈZ+\›x\¬˛$\Òç\„2§V\⁄vçzëvô£⁄£\ÒÆ\«Ììîep†F ˛x§\‹\≈v˘åW€ß\ÂN\Ù\÷\ \‚≥k¶πÖ$h>\ŒeUbΩ\‘˚’î®Rß\\\◊1aE>ä\0¯≤äv\r46äw>¥\⁄\0w>¥\Ù5}\Èh∆ñõOJ\0u>ëihán4¯Èüç=\rbO∆ú¥\ ua˘°\r2ñÇIhV4ô•™∏©ï\Í\Z}0%©sP•Iö\0ï)\Ò\‘i\ﬂ˝í\ˆ´+m3\"πBà\‹aÄ~îπF$tç4v\ˆ\Ô<\˜\€[¬™\“\\\\8D@zc¿∂idç†b¨•X\0J∞¡\Áß\Ú¨]C\√v∫ﬁ∑˛Æ¢˛\“\…\–4\È@kuëÜdöD$Üó”ù¢©-D\ÕM^\“\ı\»Z\ÎF\÷,uhcmè%ç\ L™ﬁÑ©8>\’\Õ\Ë™|#\ÒQ\—tØD˙≈Ç®˘#∫è‰∫àz?yè∆©\›jV\r¯õ©\ÍZºâ°\È\ZéëiW≤)≤\À≥8#pÆÉí	\€Z?${M\Òæ%óAΩä˝\ﬁ>CZ∑\ÓÆ\0#±ä@\«˝\¬{VººÆ\›ô\ÿyô\È\\è\≈).t≠7\√˛%∑Y\'ˇ\0ÑwS[ª∏\‡B\“5úã\ÂN~\Ô\'\–WZ\ #lL\ˆ\Á•>\"@a◊Ç§q∑\∆Pk8æWpµ\Œ-µ\À?âö•éù\·π\·\‘<-c\rÓ´≠B\Õ\‰\\4L^kc\—\…u\›Iûq]\÷˝Õ∏\ı™\–\⁄\«mä£Çù±BÅgæzüÆU≤ZX±ü§¯^\rX\’\Ô≠nÆ\ﬂTê\\M¶˛\Ï€≠¡˚\”(€ëª∫\÷\ \‘kO©˙ë*<‘øç+\n\„\ÛE2üR!\ÙØBR\Û\ÎJ√πöª˛ŸªwÀ∑•l¡XWSò\Ô%RCm\À\«=kn⁄ãµ¯‘ë\‘Köz\—afù¯\”6üJu\Í7\Z9\ı•Ze”π\ı¶füœ≠\0˙e>Ä$Jíò¶üö\0ì\Ò•\Á÷ôöv}\ÈXß\Ê£¸i\Zêö)î˙\0}/\„M\Õ-UÄu>ôO¶“•\ÕFî¥\0˙vi¥Püç/>¥\⁄vhw2å«æK»äN}h•™$*∆¢©òœ≠=)ï5\0l•\‹?º(\‹?º)XwIM\ﬂN¸iXC\ÛE2üHaE˙´w>¥l•ßTÄª9Rì4ˇ\0∆ò≈©ø\Zç)Ÿ¨\ƒ.S÷ä7J(\„J*,˙~îõh,≠K∂¨y4õ(æ\ Jõ\À\ˆ£\À\ˆ†sOZL\ZZ\0u;4\⁄]ß“Äî¥âN†	3N¸j8\È\Ù\0\Í}2üA/@©y\ı¶füœ≠}i\Ù\ }X\Û\ÎE\'\„K@æ3÷µ]7M∞ÉFÜgøøªKEΩXL…ß+}˘\ŸdÅ\ÔMá\·oÖ\Ôñ™i\«ƒóm\Ú\›^Gögc˝\–H	ˇ\0\0\€[\Ò\◊=\Òo\r+/\Ÿ\…=\Ê£8∑∫ºÜ\Ê(d¥µ?\ÎÑ\rÁ∑•\\]›ô>\»◊ûH\‚öK\€8o\Ôm¨¶î˘è%¥s∫\∆˘?{Ç>ï\—i∫≠Æ®◊´l\Â˛\≈r\÷\“>2≠\"™3=¿\À)\˜W3i\·}R˙\Œ-7PºáC\\‰\‚\ﬁ\r@f\À\n≤]Æ¿/\'`BMu\ZmçÆècocckÖï∏\€µ∫T_aú=\…4J€¢¢c\ÎöN•\„+õ˝\Z\Ú#ßxH*\Ï˘à\◊:¿b\„>Tß˝cv\“\Õ\€Mo$*÷ìFaxT`yev\„öLüZí¶\Ï±ë\·}\'Q\—,SOºøáSµ¥åAes\Â∫1é“±·èΩnGMZrR/>¥˙g>¥\Ù†”©¥øç;Ä\Íô*<”≥T!\Ù˙f\·\ÎBTöùœ≠34\Ô∆Ä2uU\Ÿq+∏oQíqœ•nY˝≈¨-x\∆\€\Ã-ü¥/›≠ª\ıt\Â\œ∆§®R§ZM¯\“\”3K\ÊèJ>ùQ+¸¥+\ZKR~5\„N\ﬁhj}GüzM\‘>iﬂçGö7J\0±EEæç\‘*±©´n©7öVj~j4•¢¿?4\Ï\‘t\Í`Hï&j4©6èZ\0};üZO∆è∆Ä$ßfõ◊•.•\0:äL”ø\Z\0^}i\Ù\Ã\”\Ú*\…öw\„Q\Êç\«“Ä%\Õ7q\ı§7CöZ\0T•\Á÷ë)h\ı\"T>r∏øiÑ\Ùp\Z\0ûùL›ûîªè°•bâi\ı\Z\»®\≈=CI\˜T∑\–fò¢ê\‹E˙\…?\ﬁ`)>\◊3\ˆò1\Î\Ê\nÄ>ï$j}\rQ˛\⁄”ó•˝©ˇ\0∂\À˛5<zï≥åÇd\Ù\…	˛Tjìp\ı®\Z˙\Í\\}b4\Ô∑E˝˘\Ô‘ü\·J¿M∏˙QQ}≤\ˆˇ\0\Ô\”QHì)6ˇ\0≥˙Tî\Ó}iC\Â˚~îûY\Ù5>\r˙\–}¥l©<º\Ùßl†õ≤øó\ÌGó\ÌV6Q≤Äπ_\À\ˆßs\ÎSl¶˘t1\Ùß\Ì>îä≠R\Û\Î@Zw\„IE\0:üLß\ÊÇd/>¥≈ßgﬁÅO\Õ2ñ™\‡KN®\˜Ø\˜á\ÁRu\ËsL\«R~5\ZS\È	´è˛*u1Xz\‘\Õ\Ú˝\Ó>µ#ZJü\Ò™®∆¨©\ÈV©Ÿ®\„\›\Ë*yçó™ë¯PøçITo5+M=±uu\r±\Ùö@ü\Ã\’f\ÒõªiºGoD`M\0mRu\È\ÕUèRá\»i2G˝\Áù2Mv\¬\ﬂ˝m\‰!ø\Áòqü ™¿i\Ì\∆y£“£˚d_ô\Á.={U_¯H,∞IKî˛\Ïd\Êò\Z#d.E,uJ\ﬂPé\Ë\ÓErü\ﬁa¥˛UŒ•q˙´õ\Ê˛¯¨I™ø7N~î\Ï\÷d∑í.˘ é\ˆX≥\–T\”^<[<®n\Îû\’ :˙\ÿ\Õl†ÆÆ7U˚ ^\Ê≤\Ó/Æ#W\Ú¥˘•\€\”iE˛f≠ió\◊\roæüq•w¡@™¿k™üJuU\Û%˛\Á\ÎR\√!oº§}EIEä*=\«“åøµ\0IëIº\”cV\€\–˛TªO°†	ø\Z_∆¢\⁄\’*G\'•\0?4˙j\∆}*Eà˙\–F˙ëa\˜¶˘&Ä\r\√÷ü∏z\—\ˆ5˛\ıH∂k˝\Í\0e9*O≥ß≠J∞Z\0jR\‰µ\'í)\¬\›˘†\˜QO\‹=jEÖ)ûP\ı†+QRyâ\Ì˘\‘_e_SO\Ú\”“Ä∏zäM\ÍüyÇ˝N(XE,ñ∞Ã∏í4o\˜≤ï\0;\ÌØ@Mtûç˘R,k\ÈO\Ú\◊“Ä\ÕZpô[ß4,k∑•=U¢\–wˇ\0≤iVA\ÈO\€K¥zUí.G•>ôR%\0\"\«\'\Ò8\Óäoœª\Óü ßß-\01vï¢AR\Ó¥\Ì\√÷Ä)˝ä5nm’ø:y∞Ö∂\‚¿™\Œ\·\ÎO»†\náOÅz,ü\˜\’?\»\ˆ?ùX\‹=ih(´\ˆ0\›T¿”õO∑ëy∑å˝÷≠s\ÎJ¥\n\Âx\Ùãx\’\√\nˇ\0ª?ë©\÷\∆=ª|§\≈Nîµa>ø\Á\Úß*ï˘NH\ˆ¿©7Zkö\0ç£\›\˜î\Z_,\”\È\À@˘4T¥S∏$gﬁè∆¢˚3ˇ\0\ı©<£Yñ\n\Ùπ\˜§\ŸM\⁄}(|\Õ\–pﬁ¥ÿô\„HñY<\…Uv¥∏\∆OÆ*Jé;\Ô\ O\·@], £\'ÅN\‹=j?≥£.\“N)\À\n˙ö	FjMÇåJ#¢§\ÿ(¸(\∆mm>îˇ\0¬ùU`πÉ\ÈF\„˝\”˘T¥Tí\ı∏˙RÉª¢ì¯TõiW\‰\È@\Ìì˚ü≠;3\œ5¸\Íj}UÄálæãO\ƒ\Õ\˜d\ß“•02ßﬁ∏cˇ\0©<∑\ı©i\‹˙\–fˇ\0l”£≥H˙ó©©y\ıß“∞+Tüe/\Œ‘©SQp+Õ¶¡u˛∑\Ã?\ÓL¬ùëfäø∏\r˛\Òjù*z`S]Oç\„\¬\›_\’#\«\ı´QZ[¢\Ò?\Ôl\Êü¯”ñÄ±.\‹4jS˚ù©|•∏E\Ì\“Êùüzw´ˇ\0g˝\‹qK\Œ7o*\Ÿ\œ¯S®¢\‡;h\Ù\€˛\Í”ëG•.i\…TH\ıP:ç\‘\Ï{\nDß%@¢TõG\˜O\ÁHî˛}j\∆=\r>°©V†c˘\ı•JN}i\Ò\–∂ü_÷üœ≠1)ˇ\0ç\0*‘™∆°©®€çK∏z\‘\\˙“•\0Oœ≠*\‘j∆ü¯\–\Í^}j,‘üç\0->ôOC@~4%%/\„@E\'\„Kœ≠\0;y•\Õ3üZ(|˚\—¯\‘t˙\0u>ô¯\”\Ë\Ù\Ó}i¥\Ó}h\ËiŸ®©\ıdèß≠F¥˙\0~h¶Tπ†—∏˙S\È\€h\„\ÈOV4\Ì¥ªh*T§\ÿ)\…@\«s\ÎE˙\“\–\"Zvi¥R∞\\uQEÜ>üLß‘ÄQE\Úèí)æ_µZ\Úœ•7\Ï˛\Ù¨;ï|∫<∫±\Â\—\Â\—avQ≤¨y~ﬂ•_∑\ÈEÖbÇçÇ¶\ŸI∂ãè4¥\Ìî`\—bÆ6äv\r˙‘ÖÜ\—N\Á÷é}jÆN\Á÷é}ijB\¬R\—N†ëŸ•¶Tº˙’Äs\ÎKIœ≠?4\0˙w>¥\Ã\”˘\ı†üLß°†	¶\‹=j\Õ:ïÄù\ıß¨ï>Æ¬π>\·\ÎN¸j\nï(∞-Iê\—Q˛5\"\Zëí~4¥\Ã”ø\Z\0ë*D®\ÍO∆ù\≈bL”í¢©RêGR\Û\ÎQ%I¯”∏\«%:òî˙@I¯”ñ£\Õ?üZ\0zTâQÊú¥\0˙ó5>¥¸\–üç*SiRÄ&\Õ9*<\”\Ë\ı\"\”iŸ†\Û\ÎE˙\“~46\·\ÎFj∆§\»\ı™∞Æ>ó\Ò¶\Ó¥f§.;\Òß-Gö}O¶f§J\0§¶S\Ë\Ù\Ó}i¥\Ó}h\0ß\ÊôKN‰é©ö¥˛}jÄ)˘¶Q@Sπ\ı¶-?üZõî˙g>¥\Ù™\Ù©G\„NU¥\0S®¢¶\‡>äT#÷ñãà)VäuTº˙\‘U/\„HüZ(\Á÷ä\0˘á\À\ˆ˝(\ÚEZ\ÿ)ª)\\\n\ﬁM7…´{)ª(üó\ÌGóW6T~]\0U\Ú˝øJoñ}*\ÁóM\Ú˝øJ\0´≤õ\Â˚U\œ$Sv\”æ\ O&¨\Ï¶˘~\’%îπ¢≠44ûHßa\\≠N©vQ≤ã»®ß\Ï£\À\ˆ¢ƒå©y\ı¶˘FùÉL\Ò¢ë)\‘\0\Íì\Ò®\È\Ù\0øç-6ï(m\‘\ı5i\Ù.iŸ®©\ıb$¸jH\Í‘â@-	i\‹˙\”i\ZÅí!ßf¢\Á÷üö\0üÃßÊ´•M@\Û\ÎR•Eœ≠=(\≈9j5ßPâRf¢ßP\Í^}j.Ω*^}h\0©wZã4P˘\˜•®≥R%\0Möw\„Q”≥@©\Í$•†	∑Tπ®sN¸h]\Ùªá≠EE\0KörTq‘º˙’í	O\ÕFî¥¨\Í_∆¢©§°jjÜ•J\0}?4\ (Uß\Û\ÎQTüç\0->ôO\ÕUâK¯\”sKLs\ÎE˙\—@Sπ\ı¶%ç+\„\i˘®∑S©\\.Köw\„Q•>®`¨j\\\‘T\ÍV\ÈR\‘U-&¨\Ë£4R\0©£ß\–®£üZ*¨\Œ>_∑\ÈGó\Ì˙T\‹˙\—œ≠EÅ\ËC\Â˚~î›µcüZèÀ™∏ÆC≤õ\Â’è.è.öï¸∫<∫±∞Q∞Uh+ï|øo“ì…´~]+ πO\À>îyg“¨\Ì£m\ZKÀ¶˘~ﬂ•]\Úiû_µ+\ÂO,˙\Zoñ}*\Ôó\ÌMh\Ë∞\\©\‰\“l´^Y\Ù£\…Ç\Â_/⁄è/=*œñ})6m\È\Õ|∫J≥\Â\”|≥\È˙PtTû_∑\ÈGó\Ì˙P!º˙\—œ≠I\Â\”6üJ@%JÜì`•U\0˛}i\Ù\Ã\Z}XÆ2T52\–2L\“\”)\ı\0;üZ)?\ZZ\0ï*l\’x\ÍZ\0ü\Ò©**ñ™¿Kœ≠?5\„KRπ©ëG≠T\‹jDc@7\ËsF˙èüZ(\\\”\Í*ì\Ò†©“†©VÄ&\Õ\ }\0I¯\“\”i\Î@ß\”3NJ\0>¥R~4µV\ÈR~5;4\…œ≠üç-\0>:ì\Ò®\„ß\‘:•Zçi\’V^}h§¸ij@ó4¥\Ã\”\Ë\‘QE;à}>ôNZ°\Á÷ïi9\ı£üZ\0|t˙dt˙\0)\‘\⁄u@ß\”)\ıKRÇùG>¥S\ÈS-CR\–\ı\0ß°¶QP‘øç74¥\0\Ó}h£üZ*¿˘\Áh¶\—E@§QE\n(¢™ QEX¬ä(†\€F\⁄(†A∂õ¥QEH\—L\⁄=(¢Ä\r£“ì\ÀîQL§\ÿ(¢Ä¥R\ÌQ@ÜmmQAa¥Sh¢≥\0¢ä(\ÙQEY$à¥¥QAD‘ü\«E\0-4Q@\«S%PâSGE`>åö(®\0…©c¢ä\0~M:ä(\Ù˙(†&•¢ä\0~M=(¢Ä%£&ä(\‘¯Ë¢ÄOJ(´\‘QEÇ1dÊüìE\0\Ù©h¢††…©h¢¨—ìE\0:¶¢ä\02i\‘Q@¢ä*\…ìFMP“•¢ä\0)\‘QP\È\ÙQUÉ&ùE¿ï)\ÙQ@QP\È˘4Q@MQVˇ\Ÿ','WhatsApp Image 2026-08-27 at 15.30.55.jpeg','image/jpeg',72420,NULL,'2026-08-31 07:40:18',NULL,NULL,NULL,NULL,NULL,'2026-08-31 07:25:51','2026-08-31 07:47:27','vendor',25,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(24,'VISHWESH MISHRA ','9971193899','GORAKHPUR',69,'SPLIT AC IDCACS18K5','514','524','2026-08-31 07:25:51',3,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-31 07:25:51','2026-08-31 07:29:21','vendor',25,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(25,'shuchi  shukla','1234567890','Bettaih',75,'SPLIT AC IDCACS13K3E','PKC-331','RKC-332','2026-08-31 09:14:52',3,'Completed','2026-08-30 00:00:00',NULL,'/uploads/installations/2026/08/d7d1dd5c6f2a47cf9ed54e9ab422b817.jpg',NULL,4000.00,'UPI',NULL,_binary 'âPNG\r\n\Z\n\0\0\0\rIHDR\0\0\0π\0\0\0î\0\0\0¯AxÜ\0\0\0ZPLTEˇˇˇ\0\0\0\Ê\Ê\Ê\„\„\„GGG˚˚˚UUUCCC¯¯¯OOO\Í\Í\Í\‡\‡\‡\Û\Û\Û\Ó\Ó\Ó777\›\›\›^^^<<<###...\Z\Z\Zfff)))mmm\“\“\“ttt\À\À\À~~~d∑U\0\0\rIDATxúÌúár\‰™ÜmîsN3\ˆ˚ø\Ê•\—#iÇ\Ì=◊ΩU[“à\	ã\‘¸\\ˆ\ˆg\ˆg\ˆg\ˆgœ≤¿\ÀvMÖÆ\‰-F\ÛGRõîH•\ﬂ:\ÕH\‘m\È\–D;V™¥F~\Î\√EFQ3ZRlZìj\Íî~\Ùe*#æ\\πóY3§o«åEÔª¶\»\·ÆE\Úñ_˘:π\ \r£[J\…\˜3ã\ÿ\€1c˛Yr,º¢\„Wâã<R\Â6û%\˜_M˛≤2?Gﬁáµ\√._\…€¨™™e\‡?sÄÅ[¨VHéI]\Òï\Ñt\Úã+≥∞?Mû,©›≤\Ó+˘ú$â?xi\ \õ`ìü¯W&\…˝@åx\y¿åßí\Î\‰]\Ê\»mINìáÆ\–A˘ï\\|±¸\…\√<IûPR9∆ç)\ZëóÆvèÖ\œ#èù\‰9ë\':πG‰çã<~≥€èëgzôo‚æò<\ˆ™≠eÅÖ<Åä\‰\"güP9?2ô\¬Å\·ÇY»ÉL\ÀÕã gW^£îaií{å±\ÃE§å•\ÀU&V<pZ√ïÖº∂ôâ*~/yF\Õ1ZôZ\»¡b9Zö\»Fl\Z-\Ì9íß•ñ[ò=@\Ó\È\‰\Õ}\‰åR\Èê\‹“á\n\ÚF\'\˜æãº4\»);UÊÇºˇy\ÚJéT\„ê€§\⁄s@M>\‰wπÜkg(\»k∏Ö˛èë7º\"E\"\n\‘<J\0\…{Yπ˝i\·]h\Â9ì\Ê˝9˝\≈\r\Û-\Z∂\ÁEB\‰∫˝jr\Ôü%\«2áD\«\ﬂBÆæsL\'\Ôì0I¶Öˇæ@7SW\Ú\Î˛ar\„PäV$æMÖF.EZ,S\‰G5øJY˘~£èQ~∂=\‰\–\√¯9\ÊûP\\5V¸U\‰45\…!úá\Ê\ﬂF~t\‹\"\»i\ \\\‰;e˛\ƒqõ∂Œê¶6∆äi±\Z~\ÏE\“\ ø]¿a\”\\4\Ú∞õ\‰EΩ\ı\Ûî\”#c≈∑º\ÿ\ZL6\‰mŸ†ïÿçC\‡º\nÀ¶™º»óP#ü!l9\ﬂ\"∑\Â\ˆ¢9˝a[zöFZQ\‰sí\€X^L>˛≥‰ø´Ã´ ∂Zaêè\„\ÿv¯\‰&˘\‹\ÚÄ£˙\Œ)Ü /\Ïô\’y\ÚπuŸªN≈•m˚$øE\Ó{º$6\Ìy)˘ª3∑˘4˘é\È#.5õsíõ=\≈˝è\Ë˘\Û»õ˝ƒå\Ò9\\¥ä(”êÆ|˘^¡®\≈8J\ﬁ%?lî¥\—*\ZÜ3ã\/Àè\ÿQrc6\˜õ»ç>tá|¸g\…gô≥\Ò+πèCsE>øñº¢a~SibtÆY¸\Á-y\Á\n\Z®\‡à>ßVv\„µ r’∂t\Üºz≥Y)>mj\"\Íì\ı£û\◊\Ùà∫\»\’|\ \»\Ú$πû˚∑ë{\‰îL -é.}/\»\·\÷$áü≤ê\Èg\◊\√\€\Û\‰î\ÂQ¡Çï|3\"PìÄwÕêúë\”%•qZl¯\˜\…3U±O˝	\Úî˛\‚™	±ë\€F\\h¶Gtü\\µáG\\ˇr\Ï’ä\…mrTò$6r√ó\Î$∑8\ÿNí“ô2,yëWt\€x\‡qëß\Ëoak\ÂÄ\‰\‡à¡[\ﬂF\ﬁB≤D\Œjr\ÿL<\À\Úrö\\ôòFí\œ6Väπ5¯{EÜ.à\»\—r]aÇ1í\Û>.\√<=≤\Õk±Cû%7gﬂèê+\’¡øF\Ó+\Úé\Ú<Héµ€úë\‰\ÿ\r™ô\Ã¸∞éÎÖí\rˇ˝I}-†Æi<F®kp\Â\–EæÆ˚\Û6˙7Xîq\Ûuy1≠∞Ã´tΩ]P\⁄\„\…Ãá\√3\Ë∞\€ZÖésn\Í1øâÉnG1\Ê\˜q\Ó\"g$ï\Ò6Ó∑í\«\≈?\‹;\\°\·\Ì,\Ô∂1å\Ãw\»I\‰∂}$òºã‹®#\¬‘ú\»e\˜é∏n{DÖ\Èk\˜\Á\»-”¶o$\◊gd¡mr#©\ﬁ¡˚$r%8∞YZáaàJ¢\˜4Àº\ E\Œ>y∏+$µ\—\÷W∑\Ëí^í,\Û2vjÑã‰óµ∑∑[	\À!b\ƒ\Ò\€\»E@∏j\‡6∫\\¯-∂êG&TT\…\ÿ$\Á\»w\ÏtOdm\œu3\Ê°\÷:\Ú\‰\÷>\‘B\ÓT>ã‹í˚\√\‰ë1\'zÑµ°\ﬁ\Ã(ó≠≤™b!	l-\‰®T\ =AN∫>¶§∑uπ\◊\\#Wä¡\√\ yE.∫\Ê£	-®¸2á+π:Ö\…XÉÆ˝\’\ B*oQπXzR¸∞QB>\˝\„\ yEnYZ\\Ú\ıì1\»3c\”\n∏\¸´\ıq…©Tm∫ª;î\Û\∆|Pî9\ˆª\‰\Ó5ù\‹XU¥ë_≥ ¨\Zh*\Îp˛J^Z\»Eô*ygî9°û#OØ≤\Ú|Bî\ÙS”≤ãTøã\’˛D>∏RπÅ¿6˚¯\‘ò†™-\ÍkA\≈/Üz>ë\ÏwU\ zyé<H•,\È\ÍVH\ı@\÷y$k\Ú\Ë	%\0\ ˘‰∫§\€™	Äjà\Ú\€FÑÜßp;Q\€ä¡{tπ;\ÔU\Í\Ãbûeò\\\ÿ:	zöCΩQ\Ìπ˙TüI\ÓT\Êl\»-^\Õ\"πIN\ÛPõ7\ıYe\ﬁ$◊≥;R\Ê\ËjR™L&u∏U4QΩj;¿E\ı{H∫\\µçvöiµ\Ã\À*5H-Pú{\—\…Sô¿ÇU|\·W–∞µv≠\›a^è\ˆDÜ•∫|\’\Ô¢\Z˙\r\Ÿ@ØT™ñ≠…Ä\¬^Wja5E´3ò7≤\'z\ÌNœπ°…¨\Ì9\Z˝&vüYTâæ\‡ªV∑±U\n¥ù	Ÿù\‰6è®±˚Ãπﬁë;\…u\’\ﬂCkNr[ô%?\\\Êwí\Ã[\r?∞\Ù3	7VW\FrB\È$O>(-0±Tâ\…\‡\„Z^u<Q∂k\…\'T\… ï\—OF\”AéEØ4\⁄T\Ê¡Hµ!]nqìºèk8\‹\Òh\˜Y.Gπ3<*ôGÅ-\‘U∆∫c®\ÌØf\€}\Ê$∑öÆoQﬂúo≤°\›;\ 5Ã∂™¯π±fa#øCStîº\’\…Ÿùe˛\Ú>59à\∆\Ò£{ÉèSB–êß$=\Ô¯áò¿C\\±\˜+òˇ°√¶ëüiùÀ¨æs$/˘]C*\Ô\Î\”h@\Ÿe\ƒ&@8ø?4Di\\‘4çòK¸*\ ap\Ù¯¸V\Ëq\‡ñ°[iFﬁ®Y\≈ƒã\ÿVâx•¢Hïéï∑ù\Ù2°\ÁI\2K\·ezDÆ\÷\ÊJU\«\’<\Ã\Ê±\⁄\Ï>s™∏)\f™èêRŒ´\ı\–Fë´y\Ë>π[9Ø»ü4’∑\‘Z\…œî˘)r\ˆ\–<4ª±V_K\Á1˙ \Z/_-\Ó∏¡rÖ∞n\Õq`%\◊6\‰>,h\‚Ω[-˙sAxD!\Ó˙s\\\·¿§ê|y“®\∆+¥π\‡a\ﬁ˙\ı~å\0í\È\Ëx¨uæjç\\÷\ÚVñò?n2\ZáGfs\∆`kcw\—9>”Ø\ÿj_ö2sá\»wê´>\Ùπä\ﬁ&d˙\Ôíó\"≠	\Õ\Íˇ7I~!\Ú\‹Fés\…\Û‰êáX\˜?uRÅ\◊l\ÿ4o9$#<¢\Í[•Äj\—˚ZØ\÷®Vq\Û˛dõV^≥¶\ÕL\Á\ÊÜ\Á\ﬂ–®¥._ÆQ\“∆ófzDu3\€\Û\Á¨YX\…-æ\‹\Áê?sµ\Â\"\˜\Ù™f\Ë\ﬂ\∆`üµs˙˚r\◊\¬yCôèê++jJ¶t\‰)\\·≥\«=Æ9M*î\n)Øﬂµ∂\≈\“ôØ˛0y¶è∏ú\‰\∆>ï;öµ}1π\˜ÚÉäÖgë;ßñ\Á…ø£\Ã3}≠«∞ô»ï2áY<l©.æ\√2∑tG\Û¶+\”\'\œ7Ω\‡\rKmsã^QYÆˇΩT≥:>üÄF\ÀC\€hÕ¶nUfxD\Ô’à˛üê∑ñá6rõ.\◊J~Ø.7\ﬂ7\◊\À…ù\rQQ\∆sWÆ\·\Zπö\Õ)\Ú\n¯‹∂;∑\À\Ú\Ëæ9e7√Üñ\”,øbo\Ÿ\Ôü\–\Óªù;f\ÛZllMÉN˛Ãì\n˛»èëw7\…\œ˘\œ/ë\Ô∞Y\'áÖ~ö):o¡,\\±Çº \Ôo™üò\◊\Ò`µN~\‡hZPô˘\—q].∫ô2˚\ﬁ\Û 7˝\ÁrWwS¨11;®Çu\Î¯∫\„Øo{—∂å<\¬H\‰j˙∂mÅ∏5èÅ[\‡/áæ\‰ƒº\Õ>\◊^E[Ot\«l\Ó\È\‰˚˚Cé‹òKR?\Ë$/ûHh´ôb]\“I^\¬B©:ßñB\ŸrM\¬\‰júj•\»-uT\ı	¨á\Í\Àwê{CWn,¥ù<CsŸîeMks∏x7.é3±í7•f\ËŸ¢ë93GaU◊º9\…-\“\‰±2\◊…≠\Á\È;\◊˝=˘Àú}˘L\«\€^èí”°π\".\ÕAëeL\…7ê∑J\‘\vê\ƒ\n8\‹\Èa±ÿ£\ﬁI¯ÅaWU_Mn\ÃÊéêS\‹.r˙Çê<\”7J˛jr£\Ã)\ﬂWì\˜FNrÀ™¡m\ÚsäÆ\„ßqÇò\Â\ÛWHr\…q¢∂H>.\*gò\…Csw\ ¸ºr˛\Ë)Ö~°IrS<≥ödâ(˝õ®\˜ü\Òt\Œ,e¨\Â°π∑\…Eßî\Ûwûiõ}´ó0•o\Ÿ\'G;7\'∫ì¸\ˆY\"wí\ﬂs÷ü\Ó5\«-\…}öY\ÿ\»g$ß](\Ë´0\‰Twî9˚\‘Nûüå≥˛0\ŸTJ\‡π\ÿ\≈\€\Z5|\»\ÒÖ.WëC]≠ë| ˝=Ø\ƒ\Ÿ\«uõm}Xóªü\Î¢˘\‘üã?Ø\‘\Â*rê’ä\”\‚\rÅmfú‹ûì˛û\ÚX@a]æ\Ê{é\‹fGŒù£o’™5hg2\ﬂ\ÿˇ\0æ]\0\Â\Ô>B	\0\0\0\0IENDÆB`Ç','sampleimage.png','image/png',3502,'/uploads/installations/2026/08/178b83db7c4348ec90a1cda52fcaabc5.jpg','2026-08-31 09:17:32',1500.00,'UPI','2026-08-31 09:18:20',1,5,'2026-08-31 09:14:52','2026-08-31 09:18:20','vendor',26,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(26,'shuchi  shukla','1234567890','Bettaih',76,'SPLIT AC IDCACS13K3E','PKC-333','RKC-333','2026-08-31 09:14:52',3,'Completed','2026-08-30 00:00:00',NULL,'/uploads/installations/2026/08/d7d1dd5c6f2a47cf9ed54e9ab422b817.jpg',NULL,4000.00,'UPI',NULL,_binary 'âPNG\r\n\Z\n\0\0\0\rIHDR\0\0\0π\0\0\0î\0\0\0¯AxÜ\0\0\0ZPLTEˇˇˇ\0\0\0\Ê\Ê\Ê\„\„\„GGG˚˚˚UUUCCC¯¯¯OOO\Í\Í\Í\‡\‡\‡\Û\Û\Û\Ó\Ó\Ó777\›\›\›^^^<<<###...\Z\Z\Zfff)))mmm\“\“\“ttt\À\À\À~~~d∑U\0\0\rIDATxúÌúár\‰™ÜmîsN3\ˆ˚ø\Ê•\—#iÇ\Ì=◊ΩU[“à\	ã\‘¸\\ˆ\ˆg\ˆg\ˆg\ˆgœ≤¿\ÀvMÖÆ\‰-F\ÛGRõîH•\ﬂ:\ÕH\‘m\È\–D;V™¥F~\Î\√EFQ3ZRlZìj\Íî~\Ùe*#æ\\πóY3§o«åEÔª¶\»\·ÆE\Úñ_˘:π\ \r£[J\…\˜3ã\ÿ\€1c˛Yr,º¢\„Wâã<R\Â6û%\˜_M˛≤2?Gﬁáµ\√._\…€¨™™e\‡?sÄÅ[¨VHéI]\Òï\Ñt\Úã+≥∞?Mû,©›≤\Ó+˘ú$â?xi\ \õ`ìü¯W&\…˝@åx\y¿åßí\Î\‰]\Ê\»mINìáÆ\–A˘ï\\|±¸\…\√<IûPR9∆ç)\ZëóÆvèÖ\œ#èù\‰9ë\':πG‰çã<~≥€èëgzôo‚æò<\ˆ™≠eÅÖ<Åä\‰\"güP9?2ô\¬Å\·ÇY»ÉL\ÀÕã gW^£îaií{å±\ÃE§å•\ÀU&V<pZ√ïÖº∂ôâ*~/yF\Õ1ZôZ\»¡b9Zö\»Fl\Z-\Ì9íß•ñ[ò=@\Ó\È\‰\Õ}\‰åR\Èê\‹“á\n\ÚF\'\˜æãº4\»);UÊÇºˇy\ÚJéT\„ê€§\⁄s@M>\‰wπÜkg(\»k∏Ö˛èë7º\"E\"\n\‘<J\0\…{Yπ˝i\·]h\Â9ì\Ê˝9˝\≈\r\Û-\Z∂\ÁEB\‰∫˝jr\Ôü%\«2áD\«\ﬂBÆæsL\'\Ôì0I¶Öˇæ@7SW\Ú\Î˛ar\„PäV$æMÖF.EZ,S\‰G5øJY˘~£èQ~∂=\‰\–\√¯9\ÊûP\\5V¸U\‰45\…!úá\Ê\ﬂF~t\‹\"\»i\ \\\‰;e˛\ƒqõ∂Œê¶6∆äi±\Z~\ÏE\“\ ø]¿a\”\\4\Ú∞õ\‰EΩ\ı\Ûî\”#c≈∑º\ÿ\ZL6\‰mŸ†ïÿçC\‡º\nÀ¶™º»óP#ü!l9\ﬂ\"∑\Â\ˆ¢9˝a[zöFZQ\‰sí\€X^L>˛≥‰ø´Ã´ ∂Zaêè\„\ÿv¯\‰&˘\‹\ÚÄ£˙\Œ)Ü /\Ïô\’y\ÚπuŸªN≈•m˚$øE\Ó{º$6\Ìy)˘ª3∑˘4˘é\È#.5õsíõ=\≈˝è\Ë˘\Û»õ˝ƒå\Ò9\\¥ä(”êÆ|˘^¡®\≈8J\ﬁ%?lî¥\—*\ZÜ3ã\/Àè\ÿQrc6\˜õ»ç>tá|¸g\…gô≥\Ò+πèCsE>øñº¢a~SibtÆY¸\Á-y\Á\n\Z®\‡à>ßVv\„µ r’∂t\Üºz≥Y)>mj\"\Íì\ı£û\◊\Ùà∫\»\’|\ \»\Ú$πû˚∑ë{\‰îL -é.}/\»\·\÷$áü≤ê\Èg\◊\√\€\Û\‰î\ÂQ¡Çï|3\"PìÄwÕêúë\”%•qZl¯\˜\…3U±O˝	\Úî˛\‚™	±ë\€F\\h¶Gtü\\µáG\\ˇr\Ï’ä\…mrTò$6r√ó\Î$∑8\ÿNí“ô2,yëWt\€x\‡qëß\Ëoak\ÂÄ\‰\‡à¡[\ﬂF\ﬁB≤D\Œjr\ÿL<\À\Úrö\\ôòFí\œ6Väπ5¯{EÜ.à\»\—r]aÇ1í\Û>.\√<=≤\Õk±Cû%7gﬂèê+\’¡øF\Ó+\Úé\Ú<Héµ€úë\‰\ÿ\r™ô\Ã¸∞éÎÖí\rˇ˝I}-†Æi<F®kp\Â\–EæÆ˚\Û6˙7Xîq\Ûuy1≠∞Ã´tΩ]P\⁄\„\…Ãá\√3\Ë∞\€ZÖésn\Í1øâÉnG1\Ê\˜q\Ó\"g$ï\Ò6Ó∑í\«\≈?\‹;\\°\·\Ì,\Ô∂1å\Ãw\»I\‰∂}$òºã‹®#\¬‘ú\»e\˜é∏n{DÖ\Èk\˜\Á\»-”¶o$\◊gd¡mr#©\ﬁ¡˚$r%8∞YZáaàJ¢\˜4Àº\ E\Œ>y∏+$µ\—\÷W∑\Ëí^í,\Û2vjÑã‰óµ∑∑[	\À!b\ƒ\Ò\€\»E@∏j\‡6∫\\¯-∂êG&TT\…\ÿ$\Á\»w\ÏtOdm\œu3\Ê°\÷:\Ú\‰\÷>\‘B\ÓT>ã‹í˚\√\‰ë1\'zÑµ°\ﬁ\Ã(ó≠≤™b!	l-\‰®T\ =AN∫>¶§∑uπ\◊\\#Wä¡\√\ yE.∫\Ê£	-®¸2á+π:Ö\…XÉÆ˝\’\ B*oQπXzR¸∞QB>\˝\„\ yEnYZ\\Ú\ıì1\»3c\”\n∏\¸´\ıq…©Tm∫ª;î\Û\∆|Pî9\ˆª\‰\Ó5ù\‹XU¥ë_≥ ¨\Zh*\Îp˛J^Z\»Eô*ygî9°û#OØ≤\Ú|Bî\ÙS”≤ãTøã\’˛D>∏RπÅ¿6˚¯\‘ò†™-\ÍkA\≈/Üz>ë\ÏwU\ zyé<H•,\È\ÍVH\ı@\÷y$k\Ú\Ë	%\0\ ˘‰∫§\€™	Äjà\Ú\€FÑÜßp;Q\€ä¡{tπ;\ÔU\Í\Ãbûeò\\\ÿ:	zöCΩQ\Ìπ˙TüI\ÓT\Êl\»-^\Õ\"πIN\ÛPõ7\ıYe\ﬁ$◊≥;R\Ê\ËjR™L&u∏U4QΩj;¿E\ı{H∫\\µçvöiµ\Ã\À*5H-Pú{\—\…Sô¿ÇU|\·W–∞µv≠\›a^è\ˆDÜ•∫|\’\Ô¢\Z˙\r\Ÿ@ØT™ñ≠…Ä\¬^Wja5E´3ò7≤\'z\ÌNœπ°…¨\Ì9\Z˝&vüYTâæ\‡ªV∑±U\n¥ù	Ÿù\‰6è®±˚Ãπﬁë;\…u\’\ﬂCkNr[ô%?\\\Êwí\Ã[\r?∞\Ù3	7VW\FrB\È$O>(-0±Tâ\…\‡\„Z^u<Q∂k\…\'T\… ï\—OF\”AéEØ4\⁄T\Ê¡Hµ!]nqìºèk8\‹\Òh\˜Y.Gπ3<*ôGÅ-\‘U∆∫c®\ÌØf\€}\Ê$∑öÆoQﬂúo≤°\›;\ 5Ã∂™¯π±fa#øCStîº\’\…Ÿùe˛\Ú>59à\∆\Ò£{ÉèSB–êß$=\Ô¯áò¿C\\±\˜+òˇ°√¶ëüiùÀ¨æs$/˘]C*\Ô\Î\”h@\Ÿe\ƒ&@8ø?4Di\\‘4çòK¸*\ ap\Ù¯¸V\Ëq\‡ñ°[iFﬁ®Y\≈ƒã\ÿVâx•¢Hïéï∑ù\Ù2°\ÁI\2K\·ezDÆ\÷\ÊJU\«\’<\Ã\Ê±\⁄\Ï>s™∏)\f™èêRŒ´\ı\–Fë´y\Ë>π[9Ø»ü4’∑\‘Z\…œî˘)r\ˆ\–<4ª±V_K\Á1˙ \Z/_-\Ó∏¡rÖ∞n\Õq`%\◊6\‰>,h\‚Ω[-˙sAxD!\Ó˙s\\\·¿§ê|y“®\∆+¥π\‡a\ﬁ˙\ı~å\0í\È\Ëx¨uæjç\\÷\ÚVñò?n2\ZáGfs\∆`kcw\—9>”Ø\ÿj_ö2sá\»wê´>\Ùπä\ﬁ&d˙\Ôíó\"≠	\Õ\Íˇ7I~!\Ú\‹Fés\…\Û‰êáX\˜?uRÅ\◊l\ÿ4o9$#<¢\Í[•Äj\—˚ZØ\÷®Vq\Û˛dõV^≥¶\ÕL\Á\ÊÜ\Á\ﬂ–®¥._ÆQ\“∆ófzDu3\€\Û\Á¨YX\…-æ\‹\Áê?sµ\Â\"\˜\Ù™f\Ë\ﬂ\∆`üµs˙˚r\◊\¬yCôèê++jJ¶t\‰)\\·≥\«=Æ9M*î\n)Øﬂµ∂\≈\“ôØ˛0y¶è∏ú\‰\∆>ï;öµ}1π\˜ÚÉäÖgë;ßñ\Á…ø£\Ã3}≠«∞ô»ï2áY<l©.æ\√2∑tG\Û¶+\”\'\œ7Ω\‡\rKmsã^QYÆˇΩT≥:>üÄF\ÀC\€hÕ¶nUfxD\Ô’à˛üê∑ñá6rõ.\◊J~Ø.7\ﬂ7\◊\À…ù\rQQ\∆sWÆ\·\Zπö\Õ)\Ú\n¯‹∂;∑\À\Ú\Ëæ9e7√Üñ\”,øbo\Ÿ\Ôü\–\Óªù;f\ÛZllMÉN˛Ãì\n˛»èëw7\…\œ˘\œ/ë\Ô∞Y\'áÖ~ö):o¡,\\±Çº \Ôo™üò\◊\Ò`µN~\‡hZPô˘\—q].∫ô2˚\ﬁ\Û 7˝\ÁrWwS¨11;®Çu\Î¯∫\„Øo{—∂å<\¬H\‰j˙∂mÅ∏5èÅ[\‡/áæ\‰ƒº\Õ>\◊^E[Ot\«l\Ó\È\‰˚˚Cé‹òKR?\Ë$/ûHh´ôb]\“I^\¬B©:ßñB\ŸrM\¬\‰júj•\»-uT\ı	¨á\Í\Àwê{CWn,¥ù<CsŸîeMks∏x7.é3±í7•f\ËŸ¢ë93GaU◊º9\…-\“\‰±2\◊…≠\Á\È;\◊˝=˘Àú}˘L\«\€^èí”°π\".\ÕAëeL\…7ê∑J\‘\vê\ƒ\n8\‹\Èa±ÿ£\ﬁI¯ÅaWU_Mn\ÃÊéêS\‹.r˙Çê<\”7J˛jr£\Ã)\ﬂWì\˜FNrÀ™¡m\ÚsäÆ\„ßqÇò\Â\ÛWHr\…q¢∂H>.\*gò\…Csw\ ¸ºr˛\Ë)Ö~°IrS<≥ödâ(˝õ®\˜ü\Òt\Œ,e¨\Â°π∑\…Eßî\Ûwûiõ}´ó0•o\Ÿ\'G;7\'∫ì¸\ˆY\"wí\ﬂs÷ü\Ó5\«-\…}öY\ÿ\»g$ß](\Ë´0\‰Twî9˚\‘Nûüå≥˛0\ŸTJ\‡π\ÿ\≈\€\Z5|\»\ÒÖ.WëC]≠ë| ˝=Ø\ƒ\Ÿ\«uõm}Xóªü\Î¢˘\‘üã?Ø\‘\Â*rê’ä\”\‚\rÅmfú‹ûì˛û\ÚX@a]æ\Ê{é\‹fGŒù£o’™5hg2\ﬂ\ÿˇ\0æ]\0\Â\Ô>B	\0\0\0\0IENDÆB`Ç','sampleimage.png','image/png',3502,'/uploads/installations/2026/08/178b83db7c4348ec90a1cda52fcaabc5.jpg','2026-08-31 09:17:32',1500.00,'UPI','2026-08-31 09:18:20',1,5,'2026-08-31 09:14:52','2026-08-31 09:18:20','vendor',26,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(27,'VAANIKA ','9891572565','GREATER NOIDA',88,'SPLIT AC IDCACS13K3E','10','22','2026-09-04 13:03:27',2,'Assigned',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-04 13:03:27','2026-09-05 04:53:18','vendor',27,NULL,NULL,0,NULL,'2026-09-05 04:53:18',8,'10',NULL,'2026-09-05 04:53:18',8,'Paid',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(28,'VAANIKA ','9891572565','GREATER NOIDA',89,'SPLIT AC IDCACS13K3E','12','21','2026-09-04 13:03:27',2,'Payment Pending','2026-09-03 00:00:00',NULL,'/uploads/installations/2026/09/fcf10854cffc4716a81a7fa912ac89c1.pdf',NULL,1200.00,'Cash',NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-04 13:12:55',NULL,NULL,NULL,NULL,NULL,'2026-09-04 13:03:27','2026-09-04 13:14:56','vendor',27,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(29,'VAANIKA ','9891572565','C-018, GREATER NOIDA\nGautambuddha Nagar',91,'Split AC','12','17','2026-09-05 04:21:05',3,'Installation Completed','2026-09-05 00:00:00','sdmnbfkjdbflc','/uploads/installations/2026/09/8d44306ad02f479a8726895ec177854d.pdf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-05 04:21:05','2026-09-05 07:22:16','callcenter',27,5,'aAIbRdldeKTQKWSOXYdj1yA_x6_r1o_Z',1,'2026-09-05 04:21:05','2026-09-05 05:54:29',1,'12','17','2026-09-05 06:03:59',8,'Free','','2026-09-05 06:03:59',8,'dhananjai@indcool.in',24,'installtion need  extra copoper pripen','2026-09-05 05:59:50',NULL);
/*!40000 ALTER TABLE `installation_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `installation_status_logs`
--

DROP TABLE IF EXISTS `installation_status_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `installation_status_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `installation_request_id` int NOT NULL,
  `action` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `old_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `performed_by` int DEFAULT NULL,
  `performed_role` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `metadata_json` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `performed_by` (`performed_by`),
  KEY `ix_installation_status_logs_installation_request_id` (`installation_request_id`),
  CONSTRAINT `installation_status_logs_ibfk_1` FOREIGN KEY (`installation_request_id`) REFERENCES `installation_requests` (`id`),
  CONSTRAINT `installation_status_logs_ibfk_2` FOREIGN KEY (`performed_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `installation_status_logs`
--

LOCK TABLES `installation_status_logs` WRITE;
/*!40000 ALTER TABLE `installation_status_logs` DISABLE KEYS */;
INSERT INTO `installation_status_logs` VALUES (1,29,'Created From Complaint','Pending','Pending',5,'callcenter',NULL,'{\"complaint_id\": 24, \"comp_no\": \"IDC_1788581931214\"}','2026-09-05 04:21:05'),(2,29,'Documents Requested','Pending','Document Requested',5,'callcenter',NULL,'{\"upload_url\": \"https://indcoolapplainces.com/services/public-upload/aAIbRdldeKTQKWSOXYdj1yA_x6_r1o_Z\", \"complaint_id\": 24}','2026-09-05 04:21:05'),(3,29,'Workflow Reset','Document Requested','Document Requested',8,'service','Admin reset the entire installation workflow',NULL,'2026-09-05 04:23:14'),(4,29,'Customer Document Uploaded','Document Requested','Admin Review Document',NULL,'customer','Original Purchase Bill/Invoice','{\"document_type\": \"Original Purchase Bill/Invoice\", \"file_path\": \"/uploads/installations/2026/09/6e777343f6404711aada3bfbb7b8e876.jpg\"}','2026-09-05 04:39:00'),(5,29,'Customer Document Uploaded','Admin Review Document','Admin Review Document',NULL,'customer','Purchase Order','{\"document_type\": \"Purchase Order\", \"file_path\": \"/uploads/installations/2026/09/386cf237ca62402f834ce95792859db7.pdf\"}','2026-09-05 04:39:00'),(6,29,'Order Verified','Admin Review Document','Order Verified',8,'service','Order TEST12345 verified','{\"order_id\": 27, \"order_no\": \"TEST12345\"}','2026-09-05 04:44:50'),(7,29,'Workflow Reset','Order Verified','Document Requested',8,'service','Admin reset the entire installation workflow',NULL,'2026-09-05 04:45:57'),(8,29,'Order Verified','Document Requested','Order Verified',8,'service','Order TEST12345 verified','{\"order_id\": 27, \"order_no\": \"TEST12345\"}','2026-09-05 04:57:09'),(9,29,'Engineer Serials Submitted','Assigned','Serial Pending Verification',2,'engineer',NULL,'{\"serial_count\": 1, \"serials\": [\"12\"]}','2026-09-05 05:02:05'),(10,29,'Returned to Engineer','Assigned','Returned',1,'admin',NULL,NULL,'2026-09-05 05:21:24'),(11,29,'Workflow Step Reset','Returned','Document Requested',1,'admin','test','{\"target_step\": 3}','2026-09-05 05:44:04'),(12,29,'Order Verified','Document Requested','Order Verified',1,'admin','Order TEST12345 verified','{\"order_id\": 27, \"order_no\": \"TEST12345\"}','2026-09-05 05:54:29'),(13,29,'Engineer Serials Submitted','Assigned','Serial Pending Verification',3,'engineer','installtion need  extra copoper pripen','{\"serial_count\": 1, \"serials\": [\"12\"]}','2026-09-05 05:59:50'),(14,29,'Serial Override','Serial Pending Verification','Serial Pending Verification',8,'service','Admin corrected serial to 12','{\"serial_no\": \"12\", \"serial_no_2\": \"17\"}','2026-09-05 06:03:59'),(15,29,'Serial Locked On Order','Serial Pending Verification','Serial Pending Verification',8,'service','Verified serial 12 locked on order item #91','{\"order_item_id\": 91, \"serial_no\": \"12\", \"serial_no_2\": \"17\", \"split_from_order_item_id\": 85}','2026-09-05 06:03:59'),(16,29,'Serials Verified','Serial Pending Verification','Assigned',8,'service','','{\"approved_count\": 1, \"rejected_count\": 0, \"billing_type\": \"Free\", \"split_installation_ids\": [29]}','2026-09-05 06:03:59'),(17,29,'Installation Completed','Assigned','Completion Pending Approval',3,'engineer','sdmnbfkjdbflc','{\"proof_document\": \"/uploads/installations/2026/09/8d44306ad02f479a8726895ec177854d.pdf\", \"billing_type\": \"Free\"}','2026-09-05 06:07:21'),(18,29,'Completion Approved','Completion Pending Approval','Completed',8,'service','ok done',NULL,'2026-09-05 06:08:45'),(19,29,'Workflow Step Reset','Completed','Completion Pending Approval',1,'admin','Admin rolled workflow back to step 8','{\"target_step\": 8}','2026-09-05 07:22:02'),(20,29,'Completion Approved','Completion Pending Approval','Installation Completed',1,'admin','update',NULL,'2026-09-05 07:22:16');
/*!40000 ALTER TABLE `installation_status_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `item_masters`
--

DROP TABLE IF EXISTS `item_masters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_masters` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `item_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `brand` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `unit` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hsn_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mrp` decimal(10,2) DEFAULT NULL,
  `serial_count` int NOT NULL DEFAULT '1',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `item_masters`
--

LOCK TABLES `item_masters` WRITE;
/*!40000 ALTER TABLE `item_masters` DISABLE KEYS */;
INSERT INTO `item_masters` VALUES (1,'8908012210474','AIR COOLER IDCCLR40L','Cooler','Sample cooler item','Indcool','Piece','847989',15999.00,1,1,'2026-08-20 07:32:21','2026-08-20 07:32:21',NULL),(2,'8908012210481','SPLIT AC IDCACS24K5','Split AC','Sample split AC item','Indcool','Set','841510',42999.00,2,1,'2026-08-20 07:32:21','2026-08-23 13:24:12',NULL),(3,'8908012210436','SPLIT AC IDCACS18K5','AC','Additional test item','Indcool','Piece','841510',36999.00,2,1,'2026-08-20 07:32:21','2026-08-23 13:24:26',NULL),(4,'8908012210443','WINDOW AC IDCACW15K3','AC',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(5,'8908012210450','GEYSER IDCGYS25L','Geyser',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(6,'8908012210467','FRIDGE IDCFRD250L','Fridge',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(7,'8908012210498','WINDOW AC IDCACW18K3','AC',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(8,'8908012210504','GEYSER IDCGYS15L','Geyser',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(9,'8908012210511','FRIDGE IDCFRD320L','Fridge',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(10,'8908012210528','AIR COOLER IDCCLR60L','Cooler',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(11,'8908012210535','SPLIT AC IDCACS13K3E','Split AC',NULL,NULL,'Set',NULL,NULL,2,1,'2026-08-29 12:36:51','2026-08-31 08:49:16',NULL),(12,'8908012210542','WINDOW AC IDCACW24K3E','AC',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(13,'8908012210559','GEYSER IDCWH35L','Geyser',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(14,'8908012210566','FRIDGE IDCFRD360L','Fridge',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(15,'8908012210573','AIR COOLER IDCCLR80L','Cooler',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(16,'IDC-CM-WAC','Window AC','Complaint Model',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-30 12:58:14','2026-08-30 12:58:14',NULL),(17,'IDC-CM-SAC','Split AC','Complaint Model',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-30 12:58:14','2026-08-30 12:58:14',NULL),(18,'IDC-CM-FRG','Fridge','Complaint Model',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-30 12:58:14','2026-08-30 12:58:14',NULL),(19,'IDC-CM-GYS','Geyser','Complaint Model',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-30 12:58:14','2026-08-30 12:58:14',NULL),(20,'IDC-CM-WCL','Water Cooler','Complaint Model',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-30 12:58:14','2026-08-30 12:58:14',NULL),(21,'IDC-CM-ACL','Air Cooler','Complaint Model',NULL,NULL,NULL,NULL,NULL,1,1,'2026-08-30 12:58:14','2026-08-30 12:58:14',NULL);
/*!40000 ALTER TABLE `item_masters` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `market_categories`
--

DROP TABLE IF EXISTS `market_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `parent_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `parent_id` (`parent_id`),
  CONSTRAINT `market_categories_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `market_categories` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_categories`
--

LOCK TABLES `market_categories` WRITE;
/*!40000 ALTER TABLE `market_categories` DISABLE KEYS */;
INSERT INTO `market_categories` VALUES (1,'Cooling Appliances',NULL,'2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,'Air Conditioners',1,'2026-08-20 07:32:21','2026-08-20 07:32:21'),(3,'Air Coolers',1,'2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `market_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `market_items`
--

DROP TABLE IF EXISTS `market_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sku` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `company` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `category_id` int DEFAULT NULL,
  `base_price` decimal(10,2) DEFAULT NULL,
  `mrp` decimal(10,2) DEFAULT NULL,
  `image_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Active',
  `stock_count` int NOT NULL DEFAULT '0',
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `category_id` (`category_id`),
  CONSTRAINT `market_items_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `market_categories` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_items`
--

LOCK TABLES `market_items` WRITE;
/*!40000 ALTER TABLE `market_items` DISABLE KEYS */;
INSERT INTO `market_items` VALUES (1,'SKU-AC-24K5','SPLIT AC IDCACS24K5','Indcool',2,35000.00,42999.00,'/uploads/market/ac24k5.jpg','Active',25,'Marketplace sample AC item','2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,'SKU-CLR-40L','AIR COOLER IDCCLR40L','Indcool',3,12000.00,15999.00,'/uploads/market/cooler40l.jpg','Active',40,'Marketplace sample cooler item','2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `market_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `market_order_items`
--

DROP TABLE IF EXISTS `market_order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_order_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `item_id` int DEFAULT NULL,
  `qty` int NOT NULL DEFAULT '1',
  `unit_price` decimal(10,2) DEFAULT NULL,
  `subtotal` decimal(12,2) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `market_order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `market_orders` (`id`) ON DELETE CASCADE,
  CONSTRAINT `market_order_items_ibfk_2` FOREIGN KEY (`item_id`) REFERENCES `market_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_order_items`
--

LOCK TABLES `market_order_items` WRITE;
/*!40000 ALTER TABLE `market_order_items` DISABLE KEYS */;
INSERT INTO `market_order_items` VALUES (1,1,1,1,42999.00,42999.00,'2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,1,2,3,14333.00,42999.00,'2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `market_order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `market_orders`
--

DROP TABLE IF EXISTS `market_orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `retailer_id` int DEFAULT NULL,
  `distributor_id` int DEFAULT NULL,
  `total_amount` decimal(12,2) DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Pending',
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `retailer_id` (`retailer_id`),
  KEY `distributor_id` (`distributor_id`),
  CONSTRAINT `market_orders_ibfk_1` FOREIGN KEY (`retailer_id`) REFERENCES `market_users` (`id`),
  CONSTRAINT `market_orders_ibfk_2` FOREIGN KEY (`distributor_id`) REFERENCES `market_users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_orders`
--

LOCK TABLES `market_orders` WRITE;
/*!40000 ALTER TABLE `market_orders` DISABLE KEYS */;
INSERT INTO `market_orders` VALUES (1,'MKT-ORD-0001',1,2,85998.00,'Confirmed','Marketplace sample order','2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `market_orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `market_users`
--

DROP TABLE IF EXISTS `market_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address` text COLLATE utf8mb4_unicode_ci,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `role` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Retailer',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Pending',
  `fee_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Pending',
  `onboarding_fee` decimal(10,2) DEFAULT NULL,
  `joined_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `market_users`
--

LOCK TABLES `market_users` WRITE;
/*!40000 ALTER TABLE `market_users` DISABLE KEYS */;
INSERT INTO `market_users` VALUES (1,'Retailer One','retailer1@test.com','9900000001','Shop 1, Noida','Noida','Uttar Pradesh','Retailer','Approved','Paid',5000.00,'2026-08-01 09:00:00','2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,'Distributor One','distributor1@test.com','9900000002','Warehouse 4, Delhi','Delhi','Delhi','Distributor','Approved','Paid',10000.00,'2026-08-02 10:00:00','2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `market_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_items`
--

DROP TABLE IF EXISTS `order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `item_id` int DEFAULT NULL,
  `item_code` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_no_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `item_qty` int NOT NULL,
  `pcb_warranty_years` int DEFAULT NULL,
  `component_warranty_years` int DEFAULT NULL,
  `machine_warranty_years` int DEFAULT NULL,
  `free_service_count` int NOT NULL,
  `service_consume_count` int NOT NULL,
  `installation_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dry_free_service_count` int NOT NULL DEFAULT '0',
  `wet_free_service_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE,
  CONSTRAINT `order_items_ibfk_2` FOREIGN KEY (`item_id`) REFERENCES `item_masters` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_items`
--

LOCK TABLES `order_items` WRITE;
/*!40000 ALTER TABLE `order_items` DISABLE KEYS */;
INSERT INTO `order_items` VALUES (1,1,1,'8908012210474','8908012210474-A1','8908012210474-A2',1,1,1,2,2,1,'Completed','2026-08-20 07:32:21','2026-08-20 07:32:21',0,0),(2,1,2,'8908012210481','8908012210481-B1','8908012210481-B2',1,1,1,2,2,0,'Requested','2026-08-20 07:32:21','2026-08-20 07:32:21',0,0),(3,2,3,'8908012210436','8908012210436-C1',NULL,1,1,1,1,1,0,'Not Requested','2026-08-20 07:32:21','2026-08-20 07:32:21',0,0),(7,5,3,'8908012210436','IDC-124','IDC-134',1,2,3,1,4,0,'Not Requested','2026-08-23 12:28:43','2026-08-23 13:29:22',2,2),(8,5,3,'8908012210436','IDC-125','IDC-135',1,2,3,1,4,0,'Not Requested','2026-08-23 12:28:43','2026-08-23 13:29:22',2,2),(9,5,3,'8908012210436','IDC-126','IDC-136',1,2,3,1,4,0,'Not Requested','2026-08-23 12:28:43','2026-08-23 13:29:22',2,2),(10,5,3,'8908012210436','IDC-127','IDC-137',1,2,3,1,4,0,'Not Requested','2026-08-23 12:28:43','2026-08-23 13:29:22',2,2),(11,5,3,'8908012210436','IDC-128','IDC-139',1,2,3,1,4,0,'Not Requested','2026-08-23 12:28:43','2026-08-23 13:29:22',2,2),(12,5,3,'8908012210436','IDC-129','IDC-140',1,2,3,1,4,0,'Not Requested','2026-08-23 12:28:43','2026-08-23 13:29:22',2,2),(14,6,1,NULL,'V1SN006A','V1SN2-006',2,1,2,3,2,0,'Completed','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(15,7,1,NULL,'V1SN007A','V1SN2-007',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(16,8,1,NULL,'V1SN008A','V1SN2-008',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(17,9,1,NULL,'V1SN009A','V1SN2-009',2,1,2,3,2,0,'Completed','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(18,10,1,NULL,'SN01001','SN2-10-001',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(19,10,1,NULL,'SN01002','SN2-10-002',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(20,10,1,NULL,'SN01003','SN2-10-003',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(21,11,1,NULL,'SN01101','SN2-11-001',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(22,11,1,NULL,'SN01102','SN2-11-002',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(23,11,1,NULL,'SN01103','SN2-11-003',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(24,12,1,NULL,'SN01201','SN2-12-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(25,12,1,NULL,'SN01202','SN2-12-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(26,13,1,'8908012210474','SN01301','SN2-13-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-30 13:27:47',0,0),(27,13,1,'8908012210474','SN01302','SN2-13-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-30 13:27:47',0,0),(28,14,1,NULL,'SN01401','SN2-14-001',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(29,14,1,NULL,'SN01402','SN2-14-002',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(30,14,1,NULL,'SN01403','SN2-14-003',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(31,15,1,NULL,'SN01501','SN2-15-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(32,15,1,NULL,'SN01502','SN2-15-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(33,16,1,NULL,'SN01601','SN2-16-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(34,16,1,NULL,'SN01602','SN2-16-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(35,17,1,NULL,'SN01701','SN2-17-001',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(36,17,1,NULL,'SN01702','SN2-17-002',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(37,17,1,NULL,'SN01703','SN2-17-003',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(38,18,1,NULL,'SN01801','SN2-18-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(39,18,1,NULL,'SN01802','SN2-18-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(40,19,1,NULL,'SN01901','SN2-19-001',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(41,19,1,NULL,'SN01902','SN2-19-002',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(42,19,1,NULL,'SN01903','SN2-19-003',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(43,20,1,NULL,'SN02001','SN2-20-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(44,20,1,NULL,'SN02002','SN2-20-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(45,21,1,NULL,'SN02101','SN2-21-001',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(46,21,1,NULL,'SN02102','SN2-21-002',1,1,2,3,2,0,'Pending','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(47,22,1,NULL,'SN02201','SN2-22-001',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(48,22,1,NULL,'SN02202','SN2-22-002',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(49,22,1,NULL,'SN02203','SN2-22-003',1,1,2,3,2,0,'Not Requested','2026-08-29 12:36:52','2026-08-29 12:36:52',0,0),(50,23,2,'8908012210481','E2E-SN-1-20260829130611',NULL,1,1,2,3,2,1,'Completed','2026-08-29 13:06:12','2026-08-29 13:07:06',1,1),(51,23,2,'8908012210481','E2E-SN-2-20260829130611',NULL,1,1,2,3,2,1,'Completed','2026-08-29 13:06:12','2026-08-29 13:07:09',1,1),(52,5,3,'8908012210436','IDC-120','IDC-132',1,2,3,1,4,0,'Submitted','2026-08-30 13:44:33','2026-08-30 13:44:33',2,2),(53,5,3,'8908012210436','IDC-122','IDC-133',1,2,3,1,4,0,'Submitted','2026-08-30 13:44:33','2026-08-30 13:44:33',2,2),(54,5,3,'8908012210436','IDC-121','IDC-131',1,2,3,1,4,0,'Not Requested','2026-08-30 13:44:33','2026-08-30 13:44:33',2,2),(55,5,3,'8908012210436','IDC-130','IDC-141',1,2,3,1,4,0,'Submitted','2026-08-30 14:10:01','2026-08-30 14:10:01',2,2),(56,24,11,'8908012210535',NULL,NULL,1,1,10,1,2,0,'Not Requested','2026-08-31 07:05:01','2026-08-31 07:05:01',1,1),(57,24,11,'8908012210535',NULL,NULL,1,1,10,1,2,0,'Not Requested','2026-08-31 07:05:01','2026-08-31 07:05:01',1,1),(58,24,11,'8908012210535',NULL,NULL,1,1,10,1,2,0,'Not Requested','2026-08-31 07:05:01','2026-08-31 07:05:01',1,1),(59,24,11,'8908012210535',NULL,NULL,1,1,10,1,2,0,'Not Requested','2026-08-31 07:05:01','2026-08-31 07:05:01',1,1),(60,24,11,'8908012210535',NULL,NULL,1,1,10,1,2,0,'Not Requested','2026-08-31 07:05:01','2026-08-31 07:05:01',1,1),(66,25,3,'8908012210436','516','527',1,5,10,1,2,0,'Not Requested','2026-08-31 07:13:06','2026-08-31 07:21:00',1,1),(67,25,3,'8908012210436','511','526',1,5,10,1,2,0,'Submitted','2026-08-31 07:25:51','2026-08-31 07:25:51',1,1),(68,25,3,'8908012210436','512','522',1,5,10,1,2,0,'Submitted','2026-08-31 07:25:51','2026-08-31 07:25:51',1,1),(69,25,3,'8908012210436','514','524',1,5,10,1,2,0,'Submitted','2026-08-31 07:25:51','2026-08-31 07:25:51',1,1),(70,25,3,'8908012210436','515','523',1,5,10,1,2,0,'Not Requested','2026-08-31 07:25:51','2026-08-31 07:25:51',1,1),(71,25,3,'8908012210436','513','525',1,5,10,1,2,0,'Not Requested','2026-08-31 07:25:51','2026-08-31 07:25:51',1,1),(75,26,11,'8908012210535','PKC-331','RKC-332',1,2,2,2,4,2,'Completed','2026-08-31 09:14:52','2026-09-04 05:18:56',2,2),(76,26,11,'8908012210535','PKC-333','RKC-333',1,2,2,2,4,0,'Completed','2026-08-31 09:14:52','2026-08-31 09:18:20',2,2),(77,26,11,'8908012210535','PKC-332','RKC-331',1,2,2,2,4,0,'Not Requested','2026-08-31 09:14:52','2026-08-31 09:14:52',2,2),(81,27,11,'8908012210535','13','24',1,5,5,1,4,0,'Not Requested','2026-09-04 12:54:27','2026-09-04 13:00:12',2,2),(82,27,11,'8908012210535','14','25',1,5,5,1,4,0,'Not Requested','2026-09-04 12:54:27','2026-09-04 13:00:12',2,2),(83,27,11,'8908012210535','15','26',1,5,5,1,4,0,'Not Requested','2026-09-04 12:54:27','2026-09-04 13:00:12',2,2),(84,27,11,'8908012210535','16','27',1,5,5,1,4,0,'Not Requested','2026-09-04 12:54:27','2026-09-04 13:00:12',2,2),(86,27,11,'8908012210535','18','29',1,5,5,1,4,0,'Not Requested','2026-09-04 12:54:27','2026-09-04 13:00:12',2,2),(87,27,11,'8908012210535','19','30',1,5,5,1,4,0,'Not Requested','2026-09-04 12:54:27','2026-09-04 13:00:12',2,2),(88,27,11,'8908012210535','10','22',1,5,5,1,4,0,'Submitted','2026-09-04 13:03:27','2026-09-04 13:03:27',2,2),(89,27,11,'8908012210535','12','21',1,5,5,1,4,0,'Submitted','2026-09-04 13:03:27','2026-09-04 13:03:27',2,2),(90,27,11,'8908012210535','11','23',1,5,5,1,4,0,'Not Requested','2026-09-04 13:03:27','2026-09-04 13:03:27',2,2),(91,27,11,'8908012210535','17',NULL,1,5,5,1,4,0,'Completed','2026-09-05 06:03:59','2026-09-05 06:08:45',2,2),(92,27,11,'8908012210535',NULL,'28',1,5,5,1,4,0,'Not Requested','2026-09-05 06:03:59','2026-09-05 06:03:59',2,2);
/*!40000 ALTER TABLE `order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_no` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_date` date NOT NULL,
  `oem_bill_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vendor_id` int DEFAULT NULL,
  `customer_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_contact` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_address` text COLLATE utf8mb4_unicode_ci,
  `courier_id` int DEFAULT NULL,
  `lrn_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vendor_bill_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vendor_bill_date` date DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `expected_delivery_date` date DEFAULT NULL,
  `actual_delivery_date` date DEFAULT NULL,
  `order_file_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `vendor_id` (`vendor_id`),
  KEY `courier_id` (`courier_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`id`),
  CONSTRAINT `orders_ibfk_2` FOREIGN KEY (`courier_id`) REFERENCES `couriers` (`id`),
  CONSTRAINT `orders_ibfk_3` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
INSERT INTO `orders` VALUES (1,'V1-ORDER-10ROWS-20260801','2026-08-01','OEM-1001',1,'Vendor1 Customer','9876543210','customer1@test.com','Noida','Uttar Pradesh','Tower A, Noida',1,'LRN-0001','VB-001','2026-08-01','Delivered','2026-08-02','2026-08-03','/uploads/orders/order1.pdf',1,'2026-08-20 07:32:21','2026-08-20 07:32:21',NULL),(2,'V2-ORDER-AC-20260805','2026-08-05','OEM-1002',2,'Test Customer Two','9876543211','customer2@test.com','Delhi','Delhi','Pitampura, Delhi',2,'LRN-0002','VB-002','2026-08-05','In Transit','2026-08-12',NULL,'/uploads/orders/order2.pdf',1,'2026-08-20 07:32:21','2026-08-20 07:32:21',NULL),(5,'test','2026-08-23','grg',3,'Muskan Singh','8700462626','muskandpms@gmail.com','Greater Noida','Andhra Pradesh','test',1,'213123123213','234324324','2026-08-10','Delivered','2026-08-18','2026-08-18','/uploads/orders/2026/08/9b0d30141a714261902c2147bbd2a9b4.pdf',9,'2026-08-23 12:28:43','2026-08-30 13:44:10',NULL),(6,'V1-ORD-001','2026-08-27',NULL,5,'Amit Sharma','9876543210',NULL,'Delhi',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(7,'V1-ORD-002','2026-08-24',NULL,5,'Neha Verma','9876543211',NULL,'Mumbai',NULL,NULL,NULL,NULL,NULL,NULL,'In Transit',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(8,'V1-ORD-003','2026-08-21',NULL,5,'Rajat Singh','9876543212',NULL,'Bengaluru',NULL,NULL,NULL,NULL,NULL,NULL,'Pending',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(9,'V1-ORD-004','2026-08-17',NULL,5,'Pooja Rao','9876543213',NULL,'Chennai',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(10,'VEND-ORD-201','2024-07-15',NULL,4,'Cust 1','9876543210',NULL,'Delhi',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(11,'VEND-ORD-202','2024-07-20',NULL,4,'Cust 2','9876543211',NULL,'Mumbai',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(12,'VEND-ORD-203','2024-07-10',NULL,4,'Cust S','9990000005',NULL,'TestCity',NULL,NULL,NULL,NULL,NULL,NULL,'Pending',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(13,'VEND-ORD-204','2024-06-15','21321`3`3``3',4,'Cust 3','9876543212',NULL,'Bangalore',NULL,NULL,1,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-30 13:27:47',NULL),(14,'VEND-ORD-205','2024-07-25',NULL,4,'Cust 4','9876543213',NULL,'Pune',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(15,'VEND-ORD-206','2024-08-01',NULL,4,'Cust 5','9876543216',NULL,'Hyderabad',NULL,NULL,NULL,NULL,NULL,NULL,'Pending',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(16,'VEND-ORD-207','2024-08-05',NULL,4,'Cust 6','9876543217',NULL,'Chennai',NULL,NULL,NULL,NULL,NULL,NULL,'In Transit',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(17,'VEND-ORD-208','2024-08-10',NULL,4,'Cust 7','9876543218',NULL,'Kolkata',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(18,'VEND-ORD-209','2024-08-12',NULL,4,'Cust 8','9876543219',NULL,'Ahmedabad',NULL,NULL,NULL,NULL,NULL,NULL,'Pending',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(19,'VEND-ORD-210','2024-08-16',NULL,4,'Cust 9','9876543220',NULL,'Surat',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(20,'VEND-ORD-211','2024-08-20',NULL,4,'Cust 10','9876543221',NULL,'Vadodara',NULL,NULL,NULL,NULL,NULL,NULL,'In Transit',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(21,'VEND-ORD-212','2024-08-22',NULL,4,'Cust 11','9876543222',NULL,'Coimbatore',NULL,NULL,NULL,NULL,NULL,NULL,'Pending',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(22,'VEND-ORD-213','2024-08-25',NULL,4,'Cust 12','9876543223',NULL,'Indore',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL),(23,'E2E-SRV-20260829130611','2026-08-29',NULL,4,'E2E Service Customer 20260829130611','9829130611','e2e-20260829130611@example.com','Delhi',NULL,NULL,NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,NULL,1,'2026-08-29 13:06:12','2026-08-29 13:06:12',NULL),(24,'GEMC-511TEST','2026-08-31',NULL,5,'Manoranjan Kumar','NOIDA ','manoranjan@indcool.in','NOIDA ','Uttar Pradesh','K225 SITE 5 KASNA ',NULL,NULL,NULL,NULL,'Pending','2026-09-30',NULL,'/uploads/orders/2026/08/34c0ecd213ef40c69c0c07468d498b90.pdf',4,'2026-08-31 07:05:01','2026-08-31 07:05:01',NULL),(25,'5116877TEST','2026-08-31','COM55',5,'VISHWESH MISHRA ','9971193899','VISHWESH@indcool.in','GORAKHPUR','Uttar Pradesh','K255 SITE 5 KASNA ',NULL,NULL,NULL,NULL,'Delivered',NULL,NULL,'/uploads/orders/2026/08/9203a72f9c8b475c80ae26e031e3f229.pdf',4,'2026-08-31 07:13:06','2026-08-31 07:24:10',NULL),(26,'Rajeev-test-123','2026-08-31','12312412414',5,'shuchi  shukla','1234567890','dubeyrajee@gmail.com','Bettaih',NULL,'Supriya  Road',NULL,'LRN-TEST-26','VBILL-TEST-26','2026-08-30','Delivered','2026-08-31','2026-08-30','/uploads/orders/2026/08/35389a76b4954606a7e0596d8c23b4d2.jpg',4,'2026-08-31 07:51:00','2026-08-31 09:14:38',NULL),(27,'TESTqeorhjq9','2026-09-04','1111',3,'VAANIKA ','9891572565','dhananjai@indcool.in','GREATER NOIDA',NULL,'C-018, GREATER NOIDA\nGautambuddha Nagar',2,'2121','12345','2026-09-19','Pending','2026-09-20',NULL,'/uploads/orders/2026/09/57630ee2f7eb4c409f6fc8b38a5bac10.pdf',9,'2026-09-04 12:54:27','2026-09-05 06:05:23',NULL);
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `partner_agreements`
--

DROP TABLE IF EXISTS `partner_agreements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `partner_agreements` (
  `id` int NOT NULL AUTO_INCREMENT,
  `registration_id` int NOT NULL,
  `agreement_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `agreement_version` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '1.0',
  `access_token` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `signed_at` datetime DEFAULT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `otp_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `otp_expires_at` datetime DEFAULT NULL,
  `otp_attempts` int NOT NULL DEFAULT '0',
  `otp_sent_at` datetime DEFAULT NULL,
  `otp_send_count` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_partner_agreements_agreement_no` (`agreement_no`),
  UNIQUE KEY `ix_partner_agreements_access_token` (`access_token`),
  KEY `ix_partner_agreements_registration_id` (`registration_id`),
  KEY `ix_partner_agreements_email` (`email`),
  CONSTRAINT `partner_agreements_ibfk_1` FOREIGN KEY (`registration_id`) REFERENCES `partner_registrations` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `partner_agreements`
--

LOCK TABLES `partner_agreements` WRITE;
/*!40000 ALTER TABLE `partner_agreements` DISABLE KEYS */;
/*!40000 ALTER TABLE `partner_agreements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `partner_registrations`
--

DROP TABLE IF EXISTS `partner_registrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `partner_registrations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `registration_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `partner_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_person_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `onboarding_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Registration Submitted',
  `firm_address` text COLLATE utf8mb4_unicode_ci,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pincode` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gst_no` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pan_no` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gem_seller_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `admin_remark` text COLLATE utf8mb4_unicode_ci,
  `submitted_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status_updated_at` datetime DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `business_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_designation` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alternate_mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `district` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `website` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `udyam_no` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cin_no` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aadhaar_no` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `year_of_establishment` int DEFAULT NULL,
  `annual_turnover` decimal(14,2) DEFAULT NULL,
  `operating_states` text COLLATE utf8mb4_unicode_ci,
  `product_categories` text COLLATE utf8mb4_unicode_ci,
  `bank_name` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_branch` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_holder_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_number` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ifsc_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gst_certificate_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pan_card_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cancelled_cheque_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `msme_certificate_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address_proof_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `incorporation_certificate_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aadhaar_card_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `photo_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `declaration_accepted` tinyint(1) NOT NULL DEFAULT '0',
  `access_token` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `form_status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Submitted',
  `current_form_step` int NOT NULL DEFAULT '8',
  `completion_percent` int NOT NULL DEFAULT '100',
  `invited_at` datetime DEFAULT NULL,
  `form_started_at` datetime DEFAULT NULL,
  `form_submitted_at` datetime DEFAULT NULL,
  `email_resend_used` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `registration_no` (`registration_no`),
  UNIQUE KEY `ix_partner_registrations_access_token` (`access_token`),
  KEY `created_by` (`created_by`),
  KEY `ix_partner_registrations_partner_type` (`partner_type`),
  KEY `ix_partner_registrations_onboarding_status` (`onboarding_status`),
  KEY `ix_partner_registrations_mobile` (`mobile`),
  KEY `ix_partner_registrations_email` (`email`),
  CONSTRAINT `partner_registrations_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `partner_registrations`
--

LOCK TABLES `partner_registrations` WRITE;
/*!40000 ALTER TABLE `partner_registrations` DISABLE KEYS */;
INSERT INTO `partner_registrations` VALUES (1,'GEM-PART-00001','Partner','Gem Partner Solutions Pvt Ltd','9876500101','partner1@gem.example','Ravi Kumar','Documents Verification','Sample business address','Mumbai','Maharashtra','400001','27AABCU9603R1ZM',NULL,'GEM-SELLER-0001','Sample GeM partner registration',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,'BUXOaYgIdW_BjUjvNAnm_91uwYbUmImuC4GCcXYkha4','Submitted',9,100,'2026-09-05 16:40:45','2026-09-05 16:40:45','2026-09-05 16:40:45',0),(2,'GEM-PART-00002','Distributor','North India Distributors','9876500102','dist1@gem.example','Anita Sharma','Admin Review','Sample business address','Mumbai','Maharashtra','400001','27AABCU9603R2ZM',NULL,'GEM-SELLER-0002','Sample GeM partner registration',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,'Lu-jhN5aSB_avJp3ymXdr1wV3RYlvMgDd57qEmyj5sw','Submitted',9,100,'2026-09-05 16:40:45','2026-09-05 16:40:45','2026-09-05 16:40:45',0),(3,'GEM-PART-00003','Service Partner','CoolCare Service Network','9876500103','service1@gem.example','Mohit Singh','Onboarding Approved','Sample business address','Mumbai','Maharashtra','400001','27AABCU9603R3ZM',NULL,'GEM-SELLER-0003','Sample GeM partner registration',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,'nQKqjoG6QdV5yhSKpT2M92uaO-mF0D-8_POEpLVoXoE','Submitted',9,100,'2026-09-05 16:40:45','2026-09-05 16:40:45','2026-09-05 16:40:45',0),(4,'GEM-PART-00004','Retailer','City Retail Appliances','9876500104','retail1@gem.example','Priya Nair','Registration Submitted','Sample business address','Mumbai','Maharashtra','400001','27AABCU9603R4ZM',NULL,'GEM-SELLER-0004','Sample GeM partner registration',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,'yEWs3uBbt0508xxdBODvuB-rSyERRS3NfWecmunSicY','Submitted',9,100,'2026-09-05 16:40:45','2026-09-05 16:40:45','2026-09-05 16:40:45',0),(5,'GEM-PART-00005','Partner','Allied Gem Traders','9876500105','partner2@gem.example','Suresh Patel','Partner Active','Sample business address','Mumbai','Maharashtra','400001','27AABCU9603R5ZM',NULL,'GEM-SELLER-0005','Sample GeM partner registration',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,'2026-09-05 16:40:45','2026-09-05 16:40:45',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,'cs8nbNEfjGguAuo-p2_Vd_zAh7bblpBzUgPaNp0SBdI','Submitted',9,100,'2026-09-05 16:40:45','2026-09-05 16:40:45','2026-09-05 16:40:45',0),(6,'GEM-PART-00006','Partner','cepl','9891572565','cepl@indcool.in','Dhananjai','Partner Active','swdqsd','sadasd','Goa','201308','qwdqwe','qweqwe','12345678','nbln',NULL,'2026-09-06 06:23:11','2026-09-06 06:27:28',1,'2026-09-06 06:15:26','2026-09-06 06:27:28','Private Limited','director','9891572565','asdas','www.indccolin','wqeqwe','qweqw','qweqwe',2025,100.00,'jnljknlnljn','kjbjlbnlbjnl','qwdqwe','qweqwe','qwdqwed','3344444','33eeee','/uploads/partners/2026/09/78b2ff9ba73b48cf8f5494f6293ea3ca.pdf','/uploads/partners/2026/09/8b9bb58660aa4f9f8eb72f85d957dad1.pdf','/uploads/partners/2026/09/bb22941974804fe8b596a05b42ab6cfa.pdf','/uploads/partners/2026/09/a8cd64307e174d149708234f6ac50e85.pdf','/uploads/partners/2026/09/413548ede50249519e40388f6c87ca33.pdf','/uploads/partners/2026/09/acd3c3e09e594a85a69deddf2f96639e.docx','/uploads/partners/2026/09/33d1dcf9da7542328e834613e0d22a40.pdf','/uploads/partners/2026/09/f9b0e9c38b054b42ad03bd170271e64a.pdf',1,'FZho4uWbfA-NGU3APayW_lDclOCnSMDYs4v52yMy9n4','Submitted',9,100,'2026-09-06 06:15:26','2026-09-06 06:18:14','2026-09-06 06:23:11',0),(7,'GEM-PART-00007','Partner','Comtech Group','8826459036','dhanprigroup@gmail.com','Priyankatest','Invite Sent',NULL,NULL,'Andhra Pradesh',NULL,'wejrhowejfrho','werljnfw2ep','1234567','qwsdw',NULL,'2026-09-06 06:53:31','2026-09-06 06:53:31',1,'2026-09-06 06:53:31','2026-09-06 07:00:46','Proprietorship',NULL,NULL,NULL,NULL,'wefljnlwefnpkw','wekfjnlwefnp','wefnlwefn',2006,50000000.00,'PanIndia','sDAS','dfwd',NULL,'dfsd','sdfsdf','sdfsd',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,'GpU5JqC-fbo86GE2dAKfwvK3gGpV-QcfQi7YapjhB0M','In Progress',3,86,'2026-09-06 06:53:31','2026-09-06 06:57:14',NULL,0),(8,'GEM-PART-00008','Distributor','vivektest','9891572565','csdsalescentrl@indcool.in','vivek','Invite Sent',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-11 09:16:10','2026-09-11 09:16:10',1,'2026-09-11 09:16:10','2026-09-11 09:16:10',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,'rI0fpStnE7_OoP3Qo0OidfN0QfIIaMKc8meSKAAhBko','In Progress',1,50,'2026-09-11 09:16:10',NULL,NULL,0),(9,'GEM-PART-00009','Service Partner',NULL,NULL,'csdsalescentral@indcool.in',NULL,'Invite Sent',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-11 09:17:22','2026-09-11 09:17:22',1,'2026-09-11 09:17:22','2026-09-11 09:18:42','Proprietorship',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,'SyxcBOufDWr-lM3KjRMFpunnJOtZVMIXKLxBS4pTSTI','In Progress',3,43,'2026-09-11 09:17:22','2026-09-11 09:18:42',NULL,0);
/*!40000 ALTER TABLE `partner_registrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payment_transactions`
--

DROP TABLE IF EXISTS `payment_transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `payment_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_amount` decimal(12,2) NOT NULL,
  `request_count` int NOT NULL,
  `recorded_by_user_id` int DEFAULT NULL,
  `engineer_user_id` int DEFAULT NULL,
  `recorded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `recorded_by_user_id` (`recorded_by_user_id`),
  KEY `engineer_user_id` (`engineer_user_id`),
  CONSTRAINT `payment_transactions_ibfk_1` FOREIGN KEY (`recorded_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `payment_transactions_ibfk_2` FOREIGN KEY (`engineer_user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_transactions`
--

LOCK TABLES `payment_transactions` WRITE;
/*!40000 ALTER TABLE `payment_transactions` DISABLE KEYS */;
INSERT INTO `payment_transactions` VALUES (1,'UPI',1250.00,1,1,2,'2026-08-09 10:30:00'),(2,'Cash',2200.00,2,1,3,'2026-08-10 11:45:00'),(3,'Cash',500.00,1,1,NULL,'2026-08-29 13:07:13'),(4,'UPI',750.00,1,1,NULL,'2026-08-29 13:07:14'),(5,'UPI',3000.00,2,1,3,'2026-08-31 09:18:20'),(6,'UPI',2000.00,1,1,NULL,'2026-09-01 04:24:45'),(7,'UPI',3000.00,1,8,NULL,'2026-09-04 05:29:48');
/*!40000 ALTER TABLE `payment_transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `permissions`
--

DROP TABLE IF EXISTS `permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` int NOT NULL,
  `module` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sub_module` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `can_view` tinyint(1) NOT NULL,
  `can_create` tinyint(1) NOT NULL,
  `can_edit` tinyint(1) NOT NULL,
  `can_delete` tinyint(1) NOT NULL,
  `can_export` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `permissions_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=110 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `permissions`
--

LOCK TABLES `permissions` WRITE;
/*!40000 ALTER TABLE `permissions` DISABLE KEYS */;
INSERT INTO `permissions` VALUES (1,1,'dashboard',NULL,1,1,1,1,1),(2,1,'orders',NULL,1,1,1,1,1),(3,1,'installations',NULL,1,1,1,1,1),(4,1,'complaints',NULL,1,1,1,1,1),(5,1,'claims',NULL,1,1,1,1,1),(6,1,'calls',NULL,1,1,1,1,1),(7,1,'users',NULL,1,1,1,1,1),(8,2,'installations',NULL,1,0,1,0,0),(9,2,'complaints',NULL,1,0,1,0,0),(10,3,'orders',NULL,1,1,0,0,1),(11,4,'complaints',NULL,1,1,1,0,1),(12,4,'calls',NULL,1,1,1,0,1),(13,5,'dashboard',NULL,1,0,0,0,1),(14,5,'complaints','Sales',1,1,1,0,1),(15,1,'vendors',NULL,1,1,1,1,1),(16,1,'items',NULL,1,1,1,1,1),(17,1,'couriers',NULL,1,1,1,1,1),(18,1,'roles',NULL,1,1,1,1,1),(19,1,'services',NULL,1,1,1,1,1),(20,4,'dashboard',NULL,1,0,0,0,1),(21,4,'items',NULL,1,0,0,0,1),(22,4,'installations',NULL,1,0,0,0,1),(23,4,'services',NULL,1,1,0,0,0),(24,4,'orders',NULL,1,0,0,0,1),(25,4,'vendors',NULL,0,0,0,0,0),(26,4,'couriers',NULL,0,0,0,0,0),(27,4,'claims',NULL,0,0,0,0,0),(28,4,'users',NULL,0,0,0,0,0),(29,4,'roles',NULL,0,0,0,0,0),(30,2,'services',NULL,1,0,1,0,0),(31,2,'dashboard',NULL,1,0,0,0,1),(32,2,'items',NULL,1,0,0,0,1),(33,2,'orders',NULL,0,0,0,0,0),(34,2,'vendors',NULL,0,0,0,0,0),(35,2,'couriers',NULL,0,0,0,0,0),(36,2,'calls',NULL,0,0,0,0,0),(37,2,'claims',NULL,0,0,0,0,0),(38,2,'users',NULL,0,0,0,0,0),(39,2,'roles',NULL,0,0,0,0,0),(40,3,'services',NULL,1,0,1,0,0),(41,3,'dashboard',NULL,1,0,0,0,1),(42,3,'complaints',NULL,0,0,0,0,0),(43,3,'installations',NULL,0,0,0,0,0),(44,3,'vendors',NULL,0,0,0,0,0),(45,3,'items',NULL,0,0,0,0,0),(46,3,'couriers',NULL,0,0,0,0,0),(47,3,'calls',NULL,0,0,0,0,0),(48,3,'claims',NULL,0,0,0,0,0),(49,3,'users',NULL,0,0,0,0,0),(50,3,'roles',NULL,0,0,0,0,0),(51,6,'complaints',NULL,0,1,0,0,0),(52,6,'installations',NULL,0,0,0,0,0),(53,6,'orders',NULL,0,0,0,0,0),(54,6,'vendors',NULL,0,0,0,0,0),(55,6,'items',NULL,0,0,0,0,0),(56,6,'couriers',NULL,0,0,0,0,0),(57,6,'calls',NULL,0,0,0,0,0),(58,6,'claims',NULL,0,0,0,0,0),(59,6,'users',NULL,0,0,0,0,0),(60,6,'services',NULL,0,0,0,0,0),(61,6,'roles',NULL,0,0,0,0,0),(62,6,'dashboard',NULL,0,0,0,0,0),(63,5,'complaints',NULL,0,0,0,0,0),(64,5,'installations',NULL,0,0,0,0,0),(65,5,'orders',NULL,0,0,0,0,0),(66,5,'vendors',NULL,0,0,0,0,0),(67,5,'items',NULL,0,0,0,0,0),(68,5,'couriers',NULL,0,0,0,0,0),(69,5,'calls',NULL,0,0,0,0,0),(70,5,'claims',NULL,0,0,0,0,0),(71,5,'users',NULL,0,0,0,0,0),(72,5,'services',NULL,0,0,0,0,0),(73,5,'roles',NULL,0,0,0,0,0),(74,7,'complaints',NULL,1,1,1,1,1),(75,7,'installations',NULL,1,1,1,1,1),(76,7,'orders',NULL,1,1,1,1,1),(77,7,'vendors',NULL,1,1,1,1,1),(78,7,'items',NULL,1,1,1,1,1),(79,7,'couriers',NULL,1,1,1,1,1),(80,7,'calls',NULL,1,1,1,1,1),(81,7,'claims',NULL,1,1,1,1,1),(82,7,'users',NULL,0,0,0,0,0),(83,7,'services',NULL,1,1,1,1,1),(84,7,'roles',NULL,0,0,0,0,0),(85,7,'dashboard',NULL,1,1,1,1,1),(86,7,'complaints','Service',1,1,1,0,1),(87,8,'services',NULL,1,1,1,1,1),(88,8,'orders',NULL,1,1,1,1,1),(89,8,'complaints',NULL,1,1,1,1,1),(90,8,'installations',NULL,1,1,1,1,1),(91,8,'items',NULL,1,1,1,1,1),(92,8,'dashboard',NULL,1,1,1,1,1),(93,8,'vendors',NULL,1,1,1,1,1),(94,8,'couriers',NULL,1,1,1,1,1),(95,8,'calls',NULL,1,1,1,1,1),(96,8,'claims',NULL,1,1,1,1,1),(97,8,'users',NULL,0,0,0,0,0),(98,8,'roles',NULL,0,0,0,0,0),(99,7,'complaints','Installation',1,1,1,0,1),(100,7,'complaints','Sales',0,0,0,0,0),(101,7,'complaints','Others',0,0,0,0,0),(102,3,'complaints','Service',0,0,0,0,0),(103,3,'complaints','Installation',0,0,0,0,0),(104,3,'complaints','Sales',0,0,0,0,0),(105,3,'complaints','Others',0,0,0,0,0),(106,1,'complaints','Service',1,1,1,1,1),(107,1,'complaints','Installation',1,1,1,1,1),(108,1,'complaints','Sales',1,1,1,1,1),(109,1,'complaints','Others',1,1,1,1,1);
/*!40000 ALTER TABLE `permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `projects`
--

DROP TABLE IF EXISTS `projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `projects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `owner_id` (`owner_id`),
  CONSTRAINT `projects_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `projects`
--

LOCK TABLES `projects` WRITE;
/*!40000 ALTER TABLE `projects` DISABLE KEYS */;
INSERT INTO `projects` VALUES (1,'Advisor Onboarding Pilot','Sample workflow project for testing','Active',1,'2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,'Retail Campaign Setup','Secondary sample workflow project','Draft',6,'2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `projects` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES (1,'admin','Administrator ‚Äî full access to all modules','2026-08-20 07:32:21','2026-08-22 12:46:39'),(2,'engineer','Engineer ‚Äî view assigned complaints/installations, update status & work reports','2026-08-20 07:32:21','2026-08-22 12:46:39'),(3,'vendor','Vendor ‚Äî read-only access to own orders','2026-08-20 07:32:21','2026-08-22 12:46:39'),(4,'callcenter','Call Center ‚Äî create/view complaints, log calls','2026-08-20 07:32:21','2026-08-22 12:46:39'),(5,'sales','Sales ‚Äî view & create only Sales-type complaints','2026-08-20 07:32:21','2026-08-22 12:46:39'),(6,'public','Public User ‚Äî submit complaint via public form (no login UI)','2026-08-22 12:46:39','2026-08-22 12:46:39'),(7,'service','Indcool Service team (legacy role name) ‚Äî full operations access (no system admin menu)','2026-08-22 12:46:39','2026-09-01 05:02:43'),(8,'indcool_service','Indcool Service team - full operations access (no system admin menu)','2026-08-22 12:46:39','2026-09-01 03:44:03');
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `serial_history_events`
--

DROP TABLE IF EXISTS `serial_history_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `serial_history_events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_item_id` int DEFAULT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `serial_no_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_subtype` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_at` datetime NOT NULL,
  `performed_by_user_id` int DEFAULT NULL,
  `performed_by_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_table` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_id` int DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `metadata_json` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_serial_history_source_event` (`source_table`,`source_id`,`event_type`,`serial_no`),
  KEY `order_item_id` (`order_item_id`),
  KEY `performed_by_user_id` (`performed_by_user_id`),
  CONSTRAINT `serial_history_events_ibfk_1` FOREIGN KEY (`order_item_id`) REFERENCES `order_items` (`id`),
  CONSTRAINT `serial_history_events_ibfk_2` FOREIGN KEY (`performed_by_user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `serial_history_events`
--

LOCK TABLES `serial_history_events` WRITE;
/*!40000 ALTER TABLE `serial_history_events` DISABLE KEYS */;
INSERT INTO `serial_history_events` VALUES (1,1,'8908012210474-A1','8908012210474-A2','ORDER','ORDER_CREATED','2026-08-01 08:47:49',4,'vendor1','orders',1,'Order created','Order V1-ORDER-10ROWS-20260801 created for Vendor1 Customer.',NULL,'{\"order_no\":\"V1-ORDER-10ROWS-20260801\",\"status\":\"Delivered\"}','2026-08-01 08:47:49'),(2,1,'8908012210474-A1','8908012210474-A2','ORDER','EXPECTED_DELIVERY','2026-08-02 00:00:00',NULL,NULL,'orders',1000001,'Expected delivery scheduled','Expected delivery date set to 2026-08-02.',NULL,'{\"expected_delivery_date\":\"2026-08-02\"}','2026-08-01 09:00:00'),(3,1,'8908012210474-A1','8908012210474-A2','INSTALLATION','REQUEST_CREATED','2026-08-06 13:11:31',2,'Ravi Kumar','installation_requests',1,'Installation request created','Installation request 1 created with status Completed.',NULL,'{\"status\":\"Completed\",\"product_name\":\"AIR COOLER IDCCLR40L\"}','2026-08-06 13:11:31'),(4,1,'8908012210474-A1','8908012210474-A2','INSTALLATION','COMPLETED','2026-08-10 12:00:00',2,'Ravi Kumar','installation_requests',1000001,'Installation completed','Installation completed with status Completed.','Installation completed successfully','{\"status\":\"Completed\"}','2026-08-10 12:00:00'),(5,1,'8908012210474-A1','8908012210474-A2','COMPLAINT','STATUS_RESOLVED','2026-08-09 15:00:00',2,'Ravi Kumar','complaints',1,'Complaint resolved','Complaint COMP-2026-0001 marked as Resolved.','Fan motor checked and cleaned','{\"complaint_no\":\"COMP-2026-0001\"}','2026-08-09 15:00:00'),(7,50,'E2E-SN-1-20260829130611',NULL,'ORDER','ORDER_CREATED','2026-08-29 13:06:12',1,'Administrator','orders',23,'Order created','Order E2E-SRV-20260829130611 created for E2E Service Customer 20260829130611.',NULL,'{\"customer_name\": \"E2E Service Customer 20260829130611\", \"item_name\": \"SPLIT AC IDCACS24K5\", \"order_no\": \"E2E-SRV-20260829130611\", \"status\": \"Delivered\", \"vendor_name\": \"Vendor Test Co\"}','2026-08-29 13:38:51'),(8,50,'E2E-SN-1-20260829130611',NULL,'SERVICE','SERVICE_SUMMARY','2026-08-29 13:07:09',2,'Ravi Kumar','service_requests',3,'Service completed','Problem: Problem on E2E-SN-2-20260829130611. Final action: Completed work on E2E-SN-2-20260829130611',NULL,'{\"final_action\": \"Completed work on E2E-SN-2-20260829130611\", \"parts_replaced\": [], \"problem_found\": \"Problem on E2E-SN-2-20260829130611\", \"proof_document\": \"/uploads/services/2026/08/32371505661349b4b7000cd52efec5b7.pdf\", \"query_type\": \"Service\", \"request_no\": \"SRV_1788008805464\", \"service_type\": \"Free Service\", \"status\": \"Closed\", \"warranty_status\": \"IN WARRANTY\"}','2026-08-29 13:38:51'),(9,26,'SN01301','SN2-13-001','ORDER','ORDER_ITEM_UPDATED','2026-08-30 13:27:47',1,'Administrator','order_items',26,'Order line item updated','Warranty or serial details were updated from the order page.',NULL,'{\"changes\": {\"item_code\": {\"from\": null, \"to\": \"8908012210474\"}}, \"order_id\": 13, \"order_no\": \"VEND-ORD-204\"}','2026-08-30 13:27:46'),(10,27,'SN01302','SN2-13-002','ORDER','ORDER_ITEM_UPDATED','2026-08-30 13:27:47',1,'Administrator','order_items',27,'Order line item updated','Warranty or serial details were updated from the order page.',NULL,'{\"changes\": {\"item_code\": {\"from\": null, \"to\": \"8908012210474\"}}, \"order_id\": 13, \"order_no\": \"VEND-ORD-204\"}','2026-08-30 13:27:46'),(11,67,'511','526','INSTALLATION','STATUS_IN_PROGRESS','2026-08-31 00:00:00',8,'VISWESH MISHRA','installation_requests',1000022,'Installation status updated','Installation request 22 updated to In Progress.',NULL,'{\"document_path\": null, \"status\": \"In Progress\"}','2026-08-31 07:28:32'),(12,68,'512','522','INSTALLATION','COMPLETED','2026-08-29 00:00:00',3,'Sunita Patel','installation_requests',1000023,'Installation completed','Installation completed with status Settlement Approved.','1 ac installation done','{\"status\": \"Settlement Approved\", \"work_report_file_path\": \"/uploads/installations/2026/08/6c5faf58a604461298a285992eae42c5.pdf\"}','2026-08-31 07:40:01'),(13,68,'512','522','ORDER','ORDER_CREATED','2026-08-31 07:13:06',4,'Vendor One User','orders',25,'Order created','Order 5116877TEST created for VISHWESH MISHRA .',NULL,'{\"customer_name\": \"VISHWESH MISHRA \", \"item_name\": \"SPLIT AC IDCACS18K5\", \"order_no\": \"5116877TEST\", \"status\": \"Delivered\", \"vendor_name\": \"Vendor One Pvt Ltd\"}','2026-08-31 07:49:19'),(14,68,'512','522','INSTALLATION','REQUEST_CREATED','2026-08-31 07:25:51',3,'Sunita Patel','installation_requests',23,'Installation request created','Installation request 23 created with status Settlement Approved.',NULL,'{\"product_name\": \"SPLIT AC IDCACS18K5\", \"status\": \"Settlement Approved\"}','2026-08-31 07:49:19'),(16,75,'PKC-331','RKC-332','ORDER','ORDER_CREATED','2026-08-31 07:51:00',4,'Vendor One User','orders',26,'Order created','Order Rajeev-test-123 created for shuchi  shukla.',NULL,'{\"customer_name\": \"shuchi  shukla\", \"item_name\": \"SPLIT AC IDCACS13K3E\", \"order_no\": \"Rajeev-test-123\", \"status\": \"Delivered\", \"vendor_name\": \"Vendor One Pvt Ltd\"}','2026-09-01 04:25:39'),(17,75,'PKC-331','RKC-332','ORDER','EXPECTED_DELIVERY','2026-08-31 00:00:00',NULL,NULL,'orders',1000026,'Expected delivery scheduled','Expected delivery date set to 2026-08-31.',NULL,'{\"expected_delivery_date\": \"2026-08-31\"}','2026-09-01 04:25:39'),(18,75,'PKC-331','RKC-332','ORDER','ACTUAL_DELIVERY','2026-08-30 00:00:00',NULL,NULL,'orders',2000026,'Order delivered','Product delivered on 2026-08-30.',NULL,'{\"actual_delivery_date\": \"2026-08-30\"}','2026-09-01 04:25:39'),(19,75,'PKC-331','RKC-332','INSTALLATION','REQUEST_CREATED','2026-08-31 09:14:52',3,'Sunita Patel','installation_requests',25,'Installation request created','Installation request 25 created with status Completed.',NULL,'{\"product_name\": \"SPLIT AC IDCACS13K3E\", \"status\": \"Completed\"}','2026-09-01 04:25:39'),(20,75,'PKC-331','RKC-332','INSTALLATION','COMPLETED','2026-08-30 00:00:00',3,'Sunita Patel','installation_requests',1000025,'Installation completed','Installation completed with status Completed.',NULL,'{\"status\": \"Completed\", \"work_report_file_path\": \"/uploads/installations/2026/08/d7d1dd5c6f2a47cf9ed54e9ab422b817.jpg\"}','2026-09-01 04:25:39'),(21,75,'PKC-331','RKC-332','SERVICE','SERVICE_SUMMARY','2026-09-01 04:22:53',2,'Ravi Kumar','service_requests',6,'Service completed','Problem: gas issue. Final action: wewqqq. Parts replaced: gasket',NULL,'{\"final_action\": \"wewqqq\", \"parts_replaced\": [\"gasket\"], \"problem_found\": \"gas issue\", \"proof_document\": \"/uploads/services/2026/09/4054741fc470433980ff221b0bd09aeb.jpg\", \"query_type\": \"Service\", \"request_no\": \"SRV_1788232354020\", \"service_type\": \"Free Service\", \"status\": \"Service In Progress\", \"warranty_status\": \"IN WARRANTY\"}','2026-09-01 04:25:39'),(22,75,'PKC-331',NULL,'SERVICE','SERVICE_SUMMARY','2026-09-04 05:18:56',2,'Ravi Kumar','service_requests',8,'Service completed','Problem: e6  eror. Final action: replaces pcbs. Parts replaced: na','sdmfbls','{\"final_action\": \"replaces pcbs\", \"parts_replaced\": [\"na\"], \"problem_found\": \"e6  eror\", \"proof_document\": \"/uploads/services/2026/09/60aaa2a77e7846bca9b8d4a70a490059.png\", \"request_no\": \"SRV_1788494569138\", \"service_type\": \"Free Service\", \"status\": \"Service In Progress\", \"warranty_status\": \"IN WARRANTY\"}','2026-09-04 05:18:56'),(23,89,'12','21','INSTALLATION','STATUS_PAYMENT_PENDING','2026-09-03 00:00:00',8,'VISWESH MISHRA','installation_requests',1000028,'Installation status updated','Installation request 28 updated to Payment Pending.',NULL,'{\"document_path\": null, \"status\": \"Payment Pending\"}','2026-09-04 13:11:48'),(24,91,'17',NULL,'ORDER','ORDER_CREATED','2026-09-04 12:54:27',9,'IEPL','orders',27,'Order created','Order TESTqeorhjq9 created for VAANIKA .',NULL,'{\"customer_name\": \"VAANIKA \", \"item_name\": \"SPLIT AC IDCACS13K3E\", \"order_no\": \"TESTqeorhjq9\", \"status\": \"Pending\", \"vendor_name\": \"IEPL\"}','2026-09-04 13:31:31'),(25,91,'17',NULL,'ORDER','EXPECTED_DELIVERY','2026-09-20 00:00:00',NULL,NULL,'orders',1000027,'Expected delivery scheduled','Expected delivery date set to 2026-09-20.',NULL,'{\"expected_delivery_date\": \"2026-09-20\"}','2026-09-04 13:31:31'),(26,91,'17',NULL,'INSTALLATION','REQUEST_CREATED','2026-09-05 04:21:05',3,'Sunita Patel','installation_requests',29,'Installation request created','Installation request 29 created with status Installation Completed.',NULL,'{\"product_name\": \"Split AC\", \"status\": \"Installation Completed\"}','2026-09-11 09:21:25'),(27,91,'17',NULL,'INSTALLATION','COMPLETED','2026-09-05 00:00:00',3,'Sunita Patel','installation_requests',1000029,'Installation completed','Installation completed with status Installation Completed.','sdmnbfkjdbflc','{\"status\": \"Installation Completed\", \"work_report_file_path\": \"/uploads/installations/2026/09/8d44306ad02f479a8726895ec177854d.pdf\"}','2026-09-11 09:21:25');
/*!40000 ALTER TABLE `serial_history_events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_approvals`
--

DROP TABLE IF EXISTS `service_approvals`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_approvals` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `observation_id` int DEFAULT NULL,
  `decision` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `approved_by` int DEFAULT NULL,
  `approved_at` datetime NOT NULL,
  `service_request_unit_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `approved_by` (`approved_by`),
  KEY `observation_id` (`observation_id`),
  KEY `ix_service_approvals_service_request_id` (`service_request_id`),
  KEY `ix_service_approvals_service_request_unit_id` (`service_request_unit_id`),
  CONSTRAINT `service_approvals_ibfk_1` FOREIGN KEY (`approved_by`) REFERENCES `users` (`id`),
  CONSTRAINT `service_approvals_ibfk_2` FOREIGN KEY (`observation_id`) REFERENCES `service_observations` (`id`),
  CONSTRAINT `service_approvals_ibfk_3` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_approvals_service_request_unit_id_fkey` FOREIGN KEY (`service_request_unit_id`) REFERENCES `service_request_units` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_approvals`
--

LOCK TABLES `service_approvals` WRITE;
/*!40000 ALTER TABLE `service_approvals` DISABLE KEYS */;
INSERT INTO `service_approvals` VALUES (1,3,1,'Approve','Approved',1,'2026-08-29 13:07:00',1),(2,3,2,'Approve','Approved',1,'2026-08-29 13:07:02',2),(3,6,3,'Approve','please  replace ',1,'2026-09-01 04:10:01',3),(4,8,4,'Approve','Approved',8,'2026-09-04 05:13:46',5);
/*!40000 ALTER TABLE `service_approvals` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_assignments`
--

DROP TABLE IF EXISTS `service_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_assignments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `assignee_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `assignee_user_id` int DEFAULT NULL,
  `assignee_vendor_id` int DEFAULT NULL,
  `assigned_by` int DEFAULT NULL,
  `assigned_at` datetime NOT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `assigned_by` (`assigned_by`),
  KEY `ix_service_assignments_service_request_id` (`service_request_id`),
  KEY `ix_service_assignments_assignee_user_id` (`assignee_user_id`),
  KEY `ix_service_assignments_assignee_vendor_id` (`assignee_vendor_id`),
  CONSTRAINT `service_assignments_ibfk_1` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`),
  CONSTRAINT `service_assignments_ibfk_2` FOREIGN KEY (`assignee_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_assignments_ibfk_3` FOREIGN KEY (`assignee_vendor_id`) REFERENCES `vendors` (`id`),
  CONSTRAINT `service_assignments_ibfk_4` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_assignments`
--

LOCK TABLES `service_assignments` WRITE;
/*!40000 ALTER TABLE `service_assignments` DISABLE KEYS */;
/*!40000 ALTER TABLE `service_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_completions`
--

DROP TABLE IF EXISTS `service_completions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_completions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `performed_by_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `performed_by_user_id` int DEFAULT NULL,
  `performed_by_vendor_id` int DEFAULT NULL,
  `work_performed` text COLLATE utf8mb4_unicode_ci,
  `parts_replaced_json` text COLLATE utf8mb4_unicode_ci,
  `service_notes` text COLLATE utf8mb4_unicode_ci,
  `service_date` date DEFAULT NULL,
  `before_photos_json` text COLLATE utf8mb4_unicode_ci,
  `after_photos_json` text COLLATE utf8mb4_unicode_ci,
  `customer_acknowledgement_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `final_amount` decimal(12,2) DEFAULT NULL,
  `completion_remarks` text COLLATE utf8mb4_unicode_ci,
  `completed_at` datetime NOT NULL,
  `old_part_serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_part_serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `service_request_unit_id` int DEFAULT NULL,
  `engineer_completion_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `performed_by_user_id` (`performed_by_user_id`),
  KEY `performed_by_vendor_id` (`performed_by_vendor_id`),
  KEY `ix_service_completions_service_request_id` (`service_request_id`),
  KEY `ix_service_completions_service_request_unit_id` (`service_request_unit_id`),
  CONSTRAINT `service_completions_ibfk_1` FOREIGN KEY (`performed_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_completions_ibfk_2` FOREIGN KEY (`performed_by_vendor_id`) REFERENCES `vendors` (`id`),
  CONSTRAINT `service_completions_ibfk_3` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_completions_service_request_unit_id_fkey` FOREIGN KEY (`service_request_unit_id`) REFERENCES `service_request_units` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_completions`
--

LOCK TABLES `service_completions` WRITE;
/*!40000 ALTER TABLE `service_completions` DISABLE KEYS */;
INSERT INTO `service_completions` VALUES (1,3,'engineer',2,NULL,'Completed work on E2E-SN-1-20260829130611',NULL,'','2026-08-29',NULL,NULL,'/uploads/services/2026/08/37230713514e43c88b59d35f068839c0.pdf',NULL,'','2026-08-29 13:07:06',NULL,NULL,1,NULL),(2,3,'engineer',2,NULL,'Completed work on E2E-SN-2-20260829130611',NULL,'','2026-08-29',NULL,NULL,'/uploads/services/2026/08/32371505661349b4b7000cd52efec5b7.pdf',NULL,'','2026-08-29 13:07:09',NULL,NULL,2,NULL),(3,6,'engineer',2,NULL,'wewqqq',NULL,'','2026-09-01',NULL,NULL,'/uploads/services/2026/09/4054741fc470433980ff221b0bd09aeb.jpg',NULL,'','2026-09-01 04:22:53',NULL,NULL,3,'605461'),(4,8,'engineer',2,NULL,'replaces pcbs','[\"na\"]','asdljhlsD','2026-09-04',NULL,NULL,'/uploads/services/2026/09/60aaa2a77e7846bca9b8d4a70a490059.png',1200.00,'','2026-09-04 05:18:56',NULL,NULL,5,'220343');
/*!40000 ALTER TABLE `service_completions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_document_rules`
--

DROP TABLE IF EXISTS `service_document_rules`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_document_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warranty_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `query_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `document_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_required` tinyint(1) NOT NULL DEFAULT '1',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_document_rules`
--

LOCK TABLES `service_document_rules` WRITE;
/*!40000 ALTER TABLE `service_document_rules` DISABLE KEYS */;
/*!40000 ALTER TABLE `service_document_rules` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_documents`
--

DROP TABLE IF EXISTS `service_documents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `document_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploaded_by_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploaded_by_user_id` int DEFAULT NULL,
  `uploaded_by_customer_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reviewed_by` int DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_remarks` text COLLATE utf8mb4_unicode_ci,
  `uploaded_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `reviewed_by` (`reviewed_by`),
  KEY `uploaded_by_user_id` (`uploaded_by_user_id`),
  KEY `ix_service_documents_service_request_id` (`service_request_id`),
  CONSTRAINT `service_documents_ibfk_1` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`),
  CONSTRAINT `service_documents_ibfk_2` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_documents_ibfk_3` FOREIGN KEY (`uploaded_by_user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_documents`
--

LOCK TABLES `service_documents` WRITE;
/*!40000 ALTER TABLE `service_documents` DISABLE KEYS */;
INSERT INTO `service_documents` VALUES (1,4,'Original Purchase Bill/Invoice','/uploads/services/2026/08/125d7174b83b417ab5f1684c2b720edb.pdf','customer',NULL,'shivam','Reviewed',1,'2026-08-31 08:01:43','Approved','2026-08-31 07:53:55'),(2,4,'Purchase Order','/uploads/services/2026/08/9f7f1fc1dee0402ea69c651d74dc2595.jpeg','customer',NULL,'shivam','Reviewed',1,'2026-08-31 08:01:46','Approved','2026-08-31 07:53:55'),(3,5,'Original Purchase Bill/Invoice','/uploads/services/2026/08/b068a7deffda420aa3b5152ba2ba453b.pdf','customer',NULL,'shubham','Uploaded',NULL,NULL,NULL,'2026-08-31 08:06:40'),(4,5,'Purchase Order','/uploads/services/2026/08/1458505dcc754a71b12dd4d6e225c4a3.jpeg','customer',NULL,'shubham','Uploaded',NULL,NULL,NULL,'2026-08-31 08:06:40'),(5,6,'Original Purchase Bill/Invoice','/uploads/services/2026/09/b4402d2a5cbf461fad618b6ed77e65a8.jpg','customer',NULL,'dhanannjai','Reviewed',1,'2026-09-01 03:50:13','Approved','2026-09-01 03:16:57'),(6,6,'Purchase Order','/uploads/services/2026/09/8fa7f588833d446197f82a13e92270dc.jpg','customer',NULL,'dhanannjai','Reviewed',1,'2026-09-01 03:50:10','Approved','2026-09-01 03:19:16'),(7,8,'Original Purchase Bill/Invoice','/uploads/services/2026/09/4e8896cc0aa649378ac4da71c3154865.png','customer',NULL,'shuchi  shukla','Reviewed',8,'2026-09-04 04:45:36','Approved','2026-09-04 04:41:27'),(8,8,'Purchase Order','/uploads/services/2026/09/44cc87811b154be98a4f00990ff30fe0.png','customer',NULL,'shuchi  shukla','Reviewed',8,'2026-09-04 04:45:41','Approved','2026-09-04 04:41:27');
/*!40000 ALTER TABLE `service_documents` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_notifications`
--

DROP TABLE IF EXISTS `service_notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `recipient_user_id` int DEFAULT NULL,
  `recipient_vendor_id` int DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `notification_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `read_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_service_notifications_service_request_id` (`service_request_id`),
  KEY `ix_service_notifications_recipient_user_id` (`recipient_user_id`),
  KEY `ix_service_notifications_recipient_vendor_id` (`recipient_vendor_id`),
  CONSTRAINT `service_notifications_ibfk_1` FOREIGN KEY (`recipient_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_notifications_ibfk_2` FOREIGN KEY (`recipient_vendor_id`) REFERENCES `vendors` (`id`),
  CONSTRAINT `service_notifications_ibfk_3` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_notifications`
--

LOCK TABLES `service_notifications` WRITE;
/*!40000 ALTER TABLE `service_notifications` DISABLE KEYS */;
INSERT INTO `service_notifications` VALUES (1,4,1,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788162694429.','customer_document_uploaded',1,'2026-08-31 07:57:51','2026-08-31 07:53:55','2026-08-31 07:57:51'),(2,4,11,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788162694429.','customer_document_uploaded',1,NULL,'2026-08-31 07:53:55','2026-09-05 08:13:02'),(3,4,1,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788162694429.','customer_document_uploaded',1,'2026-08-31 07:57:51','2026-08-31 07:53:55','2026-08-31 07:57:51'),(4,4,11,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788162694429.','customer_document_uploaded',1,NULL,'2026-08-31 07:53:55','2026-09-05 08:13:02'),(5,5,1,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788163516751.','customer_document_uploaded',1,NULL,'2026-08-31 08:06:40','2026-09-05 08:13:03'),(6,5,11,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788163516751.','customer_document_uploaded',1,NULL,'2026-08-31 08:06:40','2026-09-05 08:13:03'),(7,5,1,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788163516751.','customer_document_uploaded',1,NULL,'2026-08-31 08:06:40','2026-09-05 08:13:03'),(8,5,11,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788163516751.','customer_document_uploaded',1,NULL,'2026-08-31 08:06:40','2026-09-05 08:13:03'),(9,6,1,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788232354020.','customer_document_uploaded',1,'2026-09-01 03:21:45','2026-09-01 03:16:57','2026-09-01 03:21:45'),(10,6,11,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788232354020.','customer_document_uploaded',1,NULL,'2026-09-01 03:16:57','2026-09-05 08:13:03'),(11,6,1,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788232354020.','customer_document_uploaded',1,'2026-09-01 03:21:45','2026-09-01 03:19:16','2026-09-01 03:21:45'),(12,6,11,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788232354020.','customer_document_uploaded',1,NULL,'2026-09-01 03:19:16','2026-09-05 08:13:03'),(13,8,1,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788494569138.','customer_document_uploaded',1,'2026-09-04 05:31:25','2026-09-04 04:41:27','2026-09-04 05:31:25'),(14,8,8,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788494569138.','customer_document_uploaded',1,'2026-09-04 04:43:30','2026-09-04 04:41:27','2026-09-04 04:43:30'),(15,8,11,NULL,'Customer documents received','Customer uploaded Original Purchase Bill/Invoice for SRV_1788494569138.','customer_document_uploaded',1,NULL,'2026-09-04 04:41:27','2026-09-05 08:13:03'),(16,8,1,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788494569138.','customer_document_uploaded',1,'2026-09-04 05:31:25','2026-09-04 04:41:27','2026-09-04 05:31:25'),(17,8,8,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788494569138.','customer_document_uploaded',1,'2026-09-04 04:43:30','2026-09-04 04:41:27','2026-09-04 04:43:30'),(18,8,11,NULL,'Customer documents received','Customer uploaded Purchase Order for SRV_1788494569138.','customer_document_uploaded',1,NULL,'2026-09-04 04:41:27','2026-09-05 08:13:03');
/*!40000 ALTER TABLE `service_notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_observations`
--

DROP TABLE IF EXISTS `service_observations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_observations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `submitted_by_user_id` int DEFAULT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warranty_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `service_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `problem_found` text COLLATE utf8mb4_unicode_ci,
  `observation` text COLLATE utf8mb4_unicode_ci,
  `recommended_action` text COLLATE utf8mb4_unicode_ci,
  `parts_required_json` text COLLATE utf8mb4_unicode_ci,
  `estimated_service_charge` decimal(12,2) DEFAULT NULL,
  `estimated_parts_charge` decimal(12,2) DEFAULT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `submitted_at` datetime NOT NULL,
  `service_request_unit_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `submitted_by_user_id` (`submitted_by_user_id`),
  KEY `ix_service_observations_service_request_id` (`service_request_id`),
  KEY `ix_service_observations_service_request_unit_id` (`service_request_unit_id`),
  CONSTRAINT `service_observations_ibfk_1` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_observations_ibfk_2` FOREIGN KEY (`submitted_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_observations_service_request_unit_id_fkey` FOREIGN KEY (`service_request_unit_id`) REFERENCES `service_request_units` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_observations`
--

LOCK TABLES `service_observations` WRITE;
/*!40000 ALTER TABLE `service_observations` DISABLE KEYS */;
INSERT INTO `service_observations` VALUES (1,3,2,'E2E-SN-1-20260829130611','IN WARRANTY','Free Service','Problem on E2E-SN-1-20260829130611','Observation for E2E-SN-1-20260829130611',NULL,NULL,NULL,NULL,NULL,'2026-08-29 13:06:56',1),(2,3,2,'E2E-SN-2-20260829130611','IN WARRANTY','Free Service','Problem on E2E-SN-2-20260829130611','Observation for E2E-SN-2-20260829130611',NULL,NULL,NULL,NULL,NULL,'2026-08-29 13:06:57',2),(3,6,2,'PKC-331','IN WARRANTY','Free Service','gas issue','replace gasket','replace gasket','[\"gasket\"]',2000.00,300.00,NULL,'2026-09-01 04:09:00',3),(4,8,2,'PKC-331','IN WARRANTY','Free Service','e6  eror','main  bora  replacement ','new pub','[\"new pub with sesonrs\"]',700.00,5000.00,'sdmfbls','2026-09-04 05:08:04',5);
/*!40000 ALTER TABLE `service_observations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_payment_requests`
--

DROP TABLE IF EXISTS `service_payment_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_payment_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `requested_by_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `requested_by_user_id` int DEFAULT NULL,
  `requested_by_vendor_id` int DEFAULT NULL,
  `service_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_charge_amount` decimal(12,2) DEFAULT NULL,
  `settlement_service_amount` decimal(12,2) DEFAULT NULL,
  `settlement_parts_amount` decimal(12,2) DEFAULT NULL,
  `total_requested_amount` decimal(12,2) DEFAULT NULL,
  `payment_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `processed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `processed_by_user_id` int DEFAULT NULL,
  `payment_transaction_id` int DEFAULT NULL,
  `payment_qr_code_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `approved_amount` decimal(12,2) DEFAULT NULL,
  `service_request_unit_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `requested_by_user_id` (`requested_by_user_id`),
  KEY `requested_by_vendor_id` (`requested_by_vendor_id`),
  KEY `ix_service_payment_requests_service_request_id` (`service_request_id`),
  KEY `processed_by_user_id` (`processed_by_user_id`),
  KEY `payment_transaction_id` (`payment_transaction_id`),
  KEY `ix_service_payment_requests_service_request_unit_id` (`service_request_unit_id`),
  CONSTRAINT `service_payment_requests_ibfk_1` FOREIGN KEY (`requested_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_payment_requests_ibfk_2` FOREIGN KEY (`requested_by_vendor_id`) REFERENCES `vendors` (`id`),
  CONSTRAINT `service_payment_requests_ibfk_3` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_payment_requests_ibfk_4` FOREIGN KEY (`processed_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_payment_requests_ibfk_5` FOREIGN KEY (`payment_transaction_id`) REFERENCES `payment_transactions` (`id`),
  CONSTRAINT `service_payment_requests_service_request_unit_id_fkey` FOREIGN KEY (`service_request_unit_id`) REFERENCES `service_request_units` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_payment_requests`
--

LOCK TABLES `service_payment_requests` WRITE;
/*!40000 ALTER TABLE `service_payment_requests` DISABLE KEYS */;
INSERT INTO `service_payment_requests` VALUES (1,3,'engineer',2,NULL,'Free Service',NULL,NULL,NULL,500.00,'Cash','E2E approved','Processed','2026-08-29 13:07:13','2026-08-29 13:07:07','2026-08-29 13:07:13',1,3,NULL,500.00,1),(2,3,'engineer',2,NULL,'Free Service',NULL,NULL,NULL,750.00,'UPI','E2E approved','Processed','2026-08-29 13:07:15','2026-08-29 13:07:10','2026-08-29 13:07:15',1,4,'/uploads/services/2026/08/5e142bb8d7984b8b8d8a52d957dcdef4.png',750.00,2),(3,6,'engineer',2,NULL,'Free Service',NULL,2000.00,300.00,2300.00,'UPI','','Processed','2026-09-01 04:24:46','2026-09-01 04:23:28','2026-09-01 04:24:46',1,6,'/uploads/services/2026/09/0fe22d27e4e04681b3eac7e596a7706e.png',2000.00,3),(4,8,'engineer',2,NULL,'Free Service',NULL,700.00,5000.00,6000.00,'UPI','','Processed','2026-09-04 05:29:48','2026-09-04 05:28:33','2026-09-04 05:29:48',8,7,'/uploads/services/2026/09/8235144495334a2cbf55e9686b3caf76.png',3000.00,5);
/*!40000 ALTER TABLE `service_payment_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_request_items`
--

DROP TABLE IF EXISTS `service_request_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_request_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `order_id` int NOT NULL,
  `item_code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `item_id` int DEFAULT NULL,
  `item_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ordered_quantity` int NOT NULL DEFAULT '0',
  `serial_count` int NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `ix_service_request_items_service_request_id` (`service_request_id`),
  KEY `ix_service_request_items_order_id` (`order_id`),
  KEY `ix_service_request_items_item_code` (`item_code`),
  CONSTRAINT `service_request_items_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `item_masters` (`id`),
  CONSTRAINT `service_request_items_ibfk_2` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `service_request_items_ibfk_3` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_request_items`
--

LOCK TABLES `service_request_items` WRITE;
/*!40000 ALTER TABLE `service_request_items` DISABLE KEYS */;
INSERT INTO `service_request_items` VALUES (1,3,23,'8908012210481',2,'SPLIT AC IDCACS24K5',2,2,'2026-08-29 13:06:48','2026-08-29 13:06:48'),(2,6,26,'8908012210535',11,'SPLIT AC IDCACS13K3E',2,2,'2026-09-01 03:52:37','2026-09-01 03:52:37'),(3,8,26,'8908012210535',11,'SPLIT AC IDCACS13K3E',2,2,'2026-09-04 04:47:20','2026-09-04 04:47:20');
/*!40000 ALTER TABLE `service_request_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_request_units`
--

DROP TABLE IF EXISTS `service_request_units`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_request_units` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `service_request_item_id` int NOT NULL,
  `order_item_id` int NOT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serial_no_2` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_engineer_id` int DEFAULT NULL,
  `assigned_at` datetime DEFAULT NULL,
  `assigned_by_user_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `serial_verified_at` datetime DEFAULT NULL,
  `warranty_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `service_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `unit_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Assigned',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_service_request_units_sr_order_item` (`service_request_id`,`order_item_id`),
  KEY `assigned_by_user_id` (`assigned_by_user_id`),
  KEY `ix_service_request_units_service_request_id` (`service_request_id`),
  KEY `ix_service_request_units_service_request_item_id` (`service_request_item_id`),
  KEY `ix_service_request_units_order_item_id` (`order_item_id`),
  KEY `ix_service_request_units_assigned_engineer_id` (`assigned_engineer_id`),
  CONSTRAINT `service_request_units_ibfk_1` FOREIGN KEY (`assigned_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_request_units_ibfk_2` FOREIGN KEY (`assigned_engineer_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_request_units_ibfk_3` FOREIGN KEY (`order_item_id`) REFERENCES `order_items` (`id`),
  CONSTRAINT `service_request_units_ibfk_4` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_request_units_ibfk_5` FOREIGN KEY (`service_request_item_id`) REFERENCES `service_request_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_request_units`
--

LOCK TABLES `service_request_units` WRITE;
/*!40000 ALTER TABLE `service_request_units` DISABLE KEYS */;
INSERT INTO `service_request_units` VALUES (1,3,1,50,'E2E-SN-1-20260829130611',NULL,2,'2026-08-29 13:06:50',1,'2026-08-29 13:06:48','2026-08-29 13:07:17','2026-08-29 13:06:54','IN WARRANTY','Free Service','Closed'),(2,3,1,51,'E2E-SN-2-20260829130611',NULL,2,'2026-08-29 13:06:50',1,'2026-08-29 13:06:48','2026-08-29 13:07:17','2026-08-29 13:06:54','IN WARRANTY','Free Service','Closed'),(3,6,2,75,'PKC-331','RKC-332',2,'2026-09-01 03:56:45',1,'2026-09-01 03:52:37','2026-09-01 04:24:46','2026-09-01 04:08:04','IN WARRANTY','Free Service','Payment Completed'),(4,6,2,76,'PKC-333','RKC-333',NULL,NULL,NULL,'2026-09-01 03:52:37','2026-09-01 03:52:37',NULL,NULL,NULL,'Assigned'),(5,8,3,75,'PKC-331','RKC-332',2,'2026-09-04 04:50:47',8,'2026-09-04 04:47:20','2026-09-04 05:29:48','2026-09-04 05:00:10','IN WARRANTY','Free Service','Payment Completed'),(6,8,3,76,'PKC-333','RKC-333',NULL,NULL,NULL,'2026-09-04 04:47:20','2026-09-04 04:47:20',NULL,NULL,NULL,'Assigned');
/*!40000 ALTER TABLE `service_request_units` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_requests`
--

DROP TABLE IF EXISTS `service_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `request_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `request_date` date NOT NULL,
  `query_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_mobile` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_address` text COLLATE utf8mb4_unicode_ci,
  `model_details` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `problem_description` text COLLATE utf8mb4_unicode_ci,
  `additional_remarks` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status_date` datetime DEFAULT NULL,
  `source` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` int DEFAULT NULL,
  `order_id` int DEFAULT NULL,
  `order_item_id` int DEFAULT NULL,
  `serial_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `service_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warranty_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_engineer_id` int DEFAULT NULL,
  `assigned_vendor_id` int DEFAULT NULL,
  `requires_documents` tinyint(1) NOT NULL DEFAULT '0',
  `ask_for_documents` tinyint(1) NOT NULL DEFAULT '0',
  `document_request_sent_at` datetime DEFAULT NULL,
  `document_access_token` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_identified_at` datetime DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `closed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `complaint_id` int DEFAULT NULL,
  `completion_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_service_requests_request_no` (`request_no`),
  KEY `created_by` (`created_by`),
  KEY `ix_service_requests_customer_mobile` (`customer_mobile`),
  KEY `ix_service_requests_status` (`status`),
  KEY `ix_service_requests_order_id` (`order_id`),
  KEY `ix_service_requests_order_item_id` (`order_item_id`),
  KEY `ix_service_requests_serial_no` (`serial_no`),
  KEY `ix_service_requests_service_type` (`service_type`),
  KEY `ix_service_requests_assigned_engineer_id` (`assigned_engineer_id`),
  KEY `ix_service_requests_assigned_vendor_id` (`assigned_vendor_id`),
  KEY `ix_service_requests_document_access_token` (`document_access_token`),
  KEY `ix_service_requests_complaint_id` (`complaint_id`),
  KEY `ix_service_requests_completion_code` (`completion_code`),
  CONSTRAINT `service_requests_ibfk_1` FOREIGN KEY (`assigned_engineer_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_requests_ibfk_2` FOREIGN KEY (`assigned_vendor_id`) REFERENCES `vendors` (`id`),
  CONSTRAINT `service_requests_ibfk_3` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
  CONSTRAINT `service_requests_ibfk_4` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CONSTRAINT `service_requests_ibfk_5` FOREIGN KEY (`order_item_id`) REFERENCES `order_items` (`id`),
  CONSTRAINT `service_requests_ibfk_6` FOREIGN KEY (`complaint_id`) REFERENCES `complaints` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_requests`
--

LOCK TABLES `service_requests` WRITE;
/*!40000 ALTER TABLE `service_requests` DISABLE KEYS */;
INSERT INTO `service_requests` VALUES (1,'SRV_1787467506532','2026-08-23','Service','PRIYANKA SINGH','08826459036','dhanprigroup@gmail.com','G1-201, ECO VILLAGE 1, GREATER NOIDA WEST- 201306','SPLIT AC ','efrSDGSADFGASDFGASFG','SDFSADFSAD','Assigned','2026-08-23 07:56:07','callcenter',5,NULL,NULL,NULL,NULL,NULL,2,NULL,0,1,'2026-08-23 06:46:47','Dbo4_Wu6DSvFLYMNns84Fttx-Cm10UYz',NULL,NULL,NULL,NULL,'2026-08-23 06:45:07','2026-08-23 06:46:47',NULL,6,NULL),(2,'SRV_1787472834960','2026-08-23','Service','Rajeev ranjan dubey','7050472288','dubeyrajee@gmail.com','Supriya  Road',NULL,'ac is making lot of noise',NULL,'Service Team Review','2026-08-23 08:13:55','callcenter',1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,0,NULL,'z7XA1VT5MqOKEV8QiZVT02hUuQiR0Kf3',NULL,NULL,NULL,NULL,'2026-08-23 08:13:55','2026-08-23 08:13:55',NULL,7,NULL),(3,'SRV_1788008805464','2026-08-29','Service','E2E Service Customer 20260829130611','9829130611','e2e-20260829130611@example.com',NULL,NULL,'E2E bulk-serial service test',NULL,'Closed','2026-08-30 11:52:36','callcenter',5,23,50,'E2E-SN-1-20260829130611','Free Service','IN WARRANTY',NULL,NULL,0,0,NULL,'RjRVaIQSLePL5HEByP3_2bxoIYDh5U3A','2026-08-29 13:06:48','2026-08-29 13:07:02','2026-08-29 13:07:06','2026-08-30 11:52:36','2026-08-29 13:06:45','2026-08-30 11:52:36',NULL,NULL,NULL),(4,'SRV_1788162694429','2026-08-31','Service','shivam','9971193899','manoranjan@indcool.in','gorakhjbd cn ','Split AC','ac free service ',NULL,'Service Team Review','2026-08-31 08:01:46','callcenter',1,25,68,'522','Free Service','IN WARRANTY',NULL,NULL,0,1,'2026-08-31 07:52:44','sEtF5J8vUoP5-wsr9ojNVRyyaPi5NKyF',NULL,NULL,NULL,NULL,'2026-08-31 07:51:34','2026-08-31 08:01:46',NULL,18,NULL),(5,'SRV_1788163516751','2026-08-31','Service','shubham','8009292355','manoranjan@indcool.in','surajpur','Split AC','ac service need ','free service ','Admin Review Document','2026-08-31 08:06:40','callcenter',5,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,1,'2026-08-31 08:06:00','U03JOfmGd-FKxZl1KYor9tuocZfpFGYZ',NULL,NULL,NULL,NULL,'2026-08-31 08:05:17','2026-08-31 08:06:40',NULL,19,NULL),(6,'SRV_1788232354020','2026-09-01','Service','shuchi  shukla','1234567890','dubeyrajee@gmail.com','Supriya  Road','Split AC','sdfsdf','sdfsdf','Service In Progress','2026-09-01 05:04:13','callcenter',5,26,75,'PKC-331','Free Service','IN WARRANTY',NULL,NULL,0,1,'2026-09-01 03:18:58','zogxPUUcv5u6Omy-MBV27InnYXpWGndK','2026-09-01 03:52:37','2026-09-01 04:10:01','2026-09-01 04:22:53',NULL,'2026-09-01 03:12:34','2026-09-01 05:04:13',NULL,20,'605461'),(7,'SRV_1788493375179','2026-09-04','Service','dhanannjai','9891572565','dhananjai@indcool.in','test new','Split AC','sdlfjns','kjahdslfjha','Service Team Review','2026-09-04 03:42:55','callcenter',5,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,1,'2026-09-04 03:49:01','k06rhRK9BH60CBsMfRWQXlTpaWi7THBY',NULL,NULL,NULL,NULL,'2026-09-04 03:42:55','2026-09-04 03:49:01',NULL,21,NULL),(8,'SRV_1788494569138','2026-09-04','Service','shuchi  shukla','1234567890','dubeyrajee@gmail.com','Supriya  Road','Split AC','dfwefdsfdsfdsf','sdfdsfsdf','Service In Progress','2026-09-04 19:30:41','callcenter',1,26,75,'PKC-331','Free Service','IN WARRANTY',NULL,NULL,0,0,'2026-09-04 04:03:46','LY6sbCrKYFxiB0P6Y0ywtwyMBgknI5KB','2026-09-04 04:47:20','2026-09-04 05:13:46','2026-09-04 05:18:56',NULL,'2026-09-04 04:02:49','2026-09-04 19:30:41',NULL,22,'220343'),(9,'SRV_1788581772757','2026-09-05','Service','dhanannjai','9891572565','dhananjai@indcool.in','test new','Split AC',NULL,NULL,'Service Team Review','2026-09-05 04:16:13','callcenter',5,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,0,NULL,'W9knt9Lv3WU36A4HYmc4P_ulHx6daa-x',NULL,NULL,NULL,NULL,'2026-09-05 04:16:13','2026-09-05 04:16:13',NULL,23,NULL);
/*!40000 ALTER TABLE `service_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_status_logs`
--

DROP TABLE IF EXISTS `service_status_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_status_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `action` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `old_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `performed_by` int DEFAULT NULL,
  `performed_role` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  `metadata_json` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  `serial_history_source_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `performed_by` (`performed_by`),
  KEY `ix_service_status_logs_service_request_id` (`service_request_id`),
  CONSTRAINT `service_status_logs_ibfk_1` FOREIGN KEY (`performed_by`) REFERENCES `users` (`id`),
  CONSTRAINT `service_status_logs_ibfk_2` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_status_logs`
--

LOCK TABLES `service_status_logs` WRITE;
/*!40000 ALTER TABLE `service_status_logs` DISABLE KEYS */;
INSERT INTO `service_status_logs` VALUES (1,3,'Request Created',NULL,'New',5,'callcenter',NULL,'{\"requested_documents\": []}','2026-08-29 13:06:45',NULL),(2,3,'Order Verified','New','Service Team Review',1,'admin',NULL,'{\"order_id\": 23, \"order_no\": \"E2E-SRV-20260829130611\"}','2026-08-29 13:06:48',NULL),(3,3,'Units Assigned','Assigned','Assigned',1,'admin',NULL,'{\"engineer_id\": 2, \"unit_ids\": [1, 2], \"quantity\": 2}','2026-08-29 13:06:50',NULL),(4,3,'Serials Verified (Bulk)','Assigned','Serial Verified',2,'engineer',NULL,'{\"unit_ids\": [1, 2]}','2026-08-29 13:06:54',NULL),(5,3,'Observation Submitted','Serial Verified','Service In Progress',2,'engineer',NULL,NULL,'2026-08-29 13:06:56',NULL),(6,3,'Observation Submitted','Service In Progress','Pending Service Approval',2,'engineer',NULL,NULL,'2026-08-29 13:06:57',NULL),(7,3,'Service Approved','Pending Service Approval','Service In Progress',1,'admin','Approved',NULL,'2026-08-29 13:07:00',NULL),(8,3,'Service Approved','Service In Progress','Service In Progress',1,'admin','Approved',NULL,'2026-08-29 13:07:02',NULL),(9,3,'Service Completed','Service In Progress','Service In Progress',2,'engineer','','{\"proof_document\": \"/uploads/services/2026/08/37230713514e43c88b59d35f068839c0.pdf\"}','2026-08-29 13:07:06',NULL),(10,3,'Payment Requested','Service In Progress','Service In Progress',2,'engineer','','{\"payment_type\": \"Cash\", \"payment_qr_code_path\": null}','2026-08-29 13:07:07',NULL),(11,3,'Service Completed','Service In Progress','Payment Requested',2,'engineer','','{\"proof_document\": \"/uploads/services/2026/08/32371505661349b4b7000cd52efec5b7.pdf\"}','2026-08-29 13:07:09',NULL),(12,3,'Payment Requested','Payment Requested','Payment Requested',2,'engineer','','{\"payment_type\": \"UPI\", \"payment_qr_code_path\": \"/uploads/services/2026/08/5e142bb8d7984b8b8d8a52d957dcdef4.png\"}','2026-08-29 13:07:10',NULL),(13,3,'Payment Approved','Payment Requested','Payment Requested',1,'admin','E2E approved','{\"payment_request_id\": 1, \"approved_amount\": 500.0, \"payment_transaction_id\": 3}','2026-08-29 13:07:13',NULL),(14,3,'Payment Approved','Payment Requested','Payment Completed',1,'admin','E2E approved','{\"payment_request_id\": 2, \"approved_amount\": 750.0, \"payment_transaction_id\": 4}','2026-08-29 13:07:15',NULL),(15,3,'Service Request Closed','Payment Completed','Closed',1,'admin',NULL,NULL,'2026-08-29 13:07:17',NULL),(16,4,'Customer Document Uploaded','Service Team Review','Admin Review Document',NULL,'customer','Original Purchase Bill/Invoice','{\"document_type\": \"Original Purchase Bill/Invoice\", \"file_path\": \"/uploads/services/2026/08/125d7174b83b417ab5f1684c2b720edb.pdf\", \"serial_no\": \"522\"}','2026-08-31 07:53:55',NULL),(17,4,'Customer Document Uploaded','Admin Review Document','Admin Review Document',NULL,'customer','Purchase Order','{\"document_type\": \"Purchase Order\", \"file_path\": \"/uploads/services/2026/08/9f7f1fc1dee0402ea69c651d74dc2595.jpeg\", \"serial_no\": \"522\"}','2026-08-31 07:53:55',NULL),(18,4,'Document Reviewed','Admin Review Document','Admin Review Document',1,'admin','Approved','{\"document_id\": 1, \"document_status\": \"Reviewed\"}','2026-08-31 08:01:43',NULL),(19,4,'Document Reviewed','Admin Review Document','Service Team Review',1,'admin','Approved','{\"document_id\": 2, \"document_status\": \"Reviewed\"}','2026-08-31 08:01:46',NULL),(20,5,'Customer Document Uploaded','Service Team Review','Admin Review Document',NULL,'customer','Original Purchase Bill/Invoice','{\"document_type\": \"Original Purchase Bill/Invoice\", \"file_path\": \"/uploads/services/2026/08/b068a7deffda420aa3b5152ba2ba453b.pdf\", \"serial_no\": null}','2026-08-31 08:06:40',NULL),(21,5,'Customer Document Uploaded','Admin Review Document','Admin Review Document',NULL,'customer','Purchase Order','{\"document_type\": \"Purchase Order\", \"file_path\": \"/uploads/services/2026/08/1458505dcc754a71b12dd4d6e225c4a3.jpeg\", \"serial_no\": null}','2026-08-31 08:06:40',NULL),(22,6,'Customer Document Uploaded','Service Team Review','Admin Review Document',NULL,'customer','Original Purchase Bill/Invoice','{\"document_type\": \"Original Purchase Bill/Invoice\", \"file_path\": \"/uploads/services/2026/09/b4402d2a5cbf461fad618b6ed77e65a8.jpg\", \"serial_no\": null}','2026-09-01 03:16:57',NULL),(23,6,'Customer Document Uploaded','Admin Review Document','Admin Review Document',NULL,'customer','Purchase Order','{\"document_type\": \"Purchase Order\", \"file_path\": \"/uploads/services/2026/09/8fa7f588833d446197f82a13e92270dc.jpg\", \"serial_no\": null}','2026-09-01 03:19:16',NULL),(24,6,'Document Reviewed','Admin Review Document','Admin Review Document',1,'admin','Approved','{\"document_id\": 6, \"document_status\": \"Reviewed\"}','2026-09-01 03:50:10',NULL),(25,6,'Document Reviewed','Admin Review Document','Service Team Review',1,'admin','Approved','{\"document_id\": 5, \"document_status\": \"Reviewed\"}','2026-09-01 03:50:13',NULL),(26,6,'Order Verified','Service Team Review','Service Team Review',1,'admin',NULL,'{\"order_id\": 26, \"order_no\": \"Rajeev-test-123\", \"serial_no\": null}','2026-09-01 03:52:37',NULL),(27,6,'Units Assigned','Assigned','Assigned',1,'admin',NULL,'{\"engineer_id\": 2, \"unit_ids\": [3], \"quantity\": 1}','2026-09-01 03:56:45',NULL),(28,6,'Serial Verified','Assigned','Engineer Visit',2,'engineer',NULL,'{\"serial_no\": \"PKC-331\", \"unit_id\": 3, \"service_type\": \"Free Service\", \"warranty_status\": \"IN WARRANTY\"}','2026-09-01 04:08:04',NULL),(29,6,'Observation Submitted','Engineer Visit','Service In Progress',2,'engineer',NULL,NULL,'2026-09-01 04:09:00',NULL),(30,6,'Service Approved','Service In Progress','Service In Progress',1,'admin','please  replace ',NULL,'2026-09-01 04:10:01',NULL),(31,6,'Service Completed','Service In Progress','Service In Progress',2,'engineer','','{\"proof_document\": \"/uploads/services/2026/09/4054741fc470433980ff221b0bd09aeb.jpg\"}','2026-09-01 04:22:53',NULL),(32,6,'Payment Requested','Service In Progress','Service In Progress',2,'engineer','','{\"payment_type\": \"UPI\", \"payment_qr_code_path\": \"/uploads/services/2026/09/0fe22d27e4e04681b3eac7e596a7706e.png\"}','2026-09-01 04:23:28',NULL),(33,6,'Payment Approved','Service In Progress','Service In Progress',1,'admin','','{\"payment_request_id\": 3, \"approved_amount\": 2000.0, \"payment_transaction_id\": 6}','2026-09-01 04:24:46',NULL),(34,7,'Documents Requested','Service Team Review','Service Team Review',8,'service',NULL,'{\"upload_url\": \"https://indcoolapplainces.com/services/public-upload/k06rhRK9BH60CBsMfRWQXlTpaWi7THBY\", \"required_documents\": [\"Original Purchase Bill/Invoice\", \"Purchase Order\"], \"requested_by_host\": \"https://www.indcoolapplainces.com\"}','2026-09-04 03:49:01',NULL),(35,7,'Document Link Resent','Service Team Review','Service Team Review',8,'service',NULL,'{\"upload_url\": \"https://indcoolapplainces.com/services/public-upload/k06rhRK9BH60CBsMfRWQXlTpaWi7THBY\", \"required_documents\": [\"Original Purchase Bill/Invoice\", \"Purchase Order\"]}','2026-09-04 04:01:19',NULL),(36,8,'Document Link Resent','Service Team Review','Service Team Review',1,'admin',NULL,'{\"upload_url\": \"https://indcoolapplainces.com/services/public-upload/LY6sbCrKYFxiB0P6Y0ywtwyMBgknI5KB\", \"required_documents\": [\"Original Purchase Bill/Invoice\", \"Purchase Order\"]}','2026-09-04 04:03:46',NULL),(37,8,'Document Link Resent','Service Team Review','Service Team Review',1,'admin',NULL,'{\"upload_url\": \"https://indcoolapplainces.com/services/public-upload/LY6sbCrKYFxiB0P6Y0ywtwyMBgknI5KB\", \"required_documents\": [\"Original Purchase Bill/Invoice\", \"Purchase Order\"]}','2026-09-04 04:24:41',NULL),(38,8,'Document Link Resent','Service Team Review','Service Team Review',1,'admin',NULL,'{\"upload_url\": \"https://indcoolapplainces.com/services/public-upload/LY6sbCrKYFxiB0P6Y0ywtwyMBgknI5KB\", \"required_documents\": [\"Original Purchase Bill/Invoice\", \"Purchase Order\"]}','2026-09-04 04:33:22',NULL),(39,8,'Customer Document Uploaded','Service Team Review','Admin Review Document',NULL,'customer','Original Purchase Bill/Invoice','{\"document_type\": \"Original Purchase Bill/Invoice\", \"file_path\": \"/uploads/services/2026/09/4e8896cc0aa649378ac4da71c3154865.png\", \"serial_no\": null}','2026-09-04 04:41:27',NULL),(40,8,'Customer Document Uploaded','Admin Review Document','Admin Review Document',NULL,'customer','Purchase Order','{\"document_type\": \"Purchase Order\", \"file_path\": \"/uploads/services/2026/09/44cc87811b154be98a4f00990ff30fe0.png\", \"serial_no\": null}','2026-09-04 04:41:27',NULL),(41,8,'Document Reviewed','Admin Review Document','Admin Review Document',8,'service','Approved','{\"document_id\": 7, \"document_status\": \"Reviewed\"}','2026-09-04 04:45:36',NULL),(42,8,'Document Reviewed','Admin Review Document','Service Team Review',8,'service','Approved','{\"document_id\": 8, \"document_status\": \"Reviewed\"}','2026-09-04 04:45:41',NULL),(43,8,'Order Verified','Service Team Review','Service Team Review',8,'service',NULL,'{\"order_id\": 26, \"order_no\": \"Rajeev-test-123\", \"serial_no\": null}','2026-09-04 04:47:20',NULL),(44,8,'Units Assigned','Assigned','Assigned',8,'service',NULL,'{\"engineer_id\": 2, \"unit_ids\": [5], \"quantity\": 1}','2026-09-04 04:50:47',NULL),(45,8,'Serial Verified','Assigned','Engineer Visit',2,'engineer',NULL,'{\"serial_no\": \"PKC-331\", \"unit_id\": 5, \"service_type\": \"Free Service\", \"warranty_status\": \"IN WARRANTY\"}','2026-09-04 05:00:10',NULL),(46,8,'Observation Submitted','Engineer Visit','Service In Progress',2,'engineer','sdmfbls',NULL,'2026-09-04 05:08:04',NULL),(47,8,'Service Approved','Service In Progress','Service In Progress',8,'service','Approved',NULL,'2026-09-04 05:13:46',NULL),(48,8,'Service Completed','Service In Progress','Service In Progress',2,'engineer','','{\"proof_document\": \"/uploads/services/2026/09/60aaa2a77e7846bca9b8d4a70a490059.png\"}','2026-09-04 05:18:56',NULL),(49,8,'Payment Requested','Service In Progress','Service In Progress',2,'engineer','','{\"payment_type\": \"UPI\", \"payment_qr_code_path\": \"/uploads/services/2026/09/8235144495334a2cbf55e9686b3caf76.png\"}','2026-09-04 05:28:33',NULL),(50,8,'Payment Approved','Service In Progress','Service In Progress',8,'service','','{\"payment_request_id\": 4, \"approved_amount\": 3000.0, \"payment_transaction_id\": 7}','2026-09-04 05:29:48',NULL);
/*!40000 ALTER TABLE `service_status_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `service_unit_assignments`
--

DROP TABLE IF EXISTS `service_unit_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `service_unit_assignments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `service_request_id` int NOT NULL,
  `service_request_unit_id` int NOT NULL,
  `engineer_id` int NOT NULL,
  `assigned_by_user_id` int DEFAULT NULL,
  `assigned_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `unassigned_at` datetime DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `remarks` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `assigned_by_user_id` (`assigned_by_user_id`),
  KEY `ix_service_unit_assignments_service_request_id` (`service_request_id`),
  KEY `ix_service_unit_assignments_service_request_unit_id` (`service_request_unit_id`),
  KEY `ix_service_unit_assignments_engineer_id` (`engineer_id`),
  CONSTRAINT `service_unit_assignments_ibfk_1` FOREIGN KEY (`assigned_by_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_unit_assignments_ibfk_2` FOREIGN KEY (`engineer_id`) REFERENCES `users` (`id`),
  CONSTRAINT `service_unit_assignments_ibfk_3` FOREIGN KEY (`service_request_id`) REFERENCES `service_requests` (`id`),
  CONSTRAINT `service_unit_assignments_ibfk_4` FOREIGN KEY (`service_request_unit_id`) REFERENCES `service_request_units` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `service_unit_assignments`
--

LOCK TABLES `service_unit_assignments` WRITE;
/*!40000 ALTER TABLE `service_unit_assignments` DISABLE KEYS */;
INSERT INTO `service_unit_assignments` VALUES (1,3,1,2,1,'2026-08-29 13:06:50',NULL,1,NULL),(2,3,2,2,1,'2026-08-29 13:06:50',NULL,1,NULL),(3,6,3,2,1,'2026-09-01 03:56:45',NULL,1,NULL),(4,8,5,2,8,'2026-09-04 04:50:47',NULL,1,NULL);
/*!40000 ALTER TABLE `service_unit_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_pending_actions`
--

DROP TABLE IF EXISTS `user_pending_actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_pending_actions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `recipient_user_id` int NOT NULL,
  `recipient_vendor_id` int DEFAULT NULL,
  `module` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_id` int NOT NULL,
  `entity_ref` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `action_type` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_label` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `href` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `occurred_at` datetime NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `read_at` datetime DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_pending_actions_recipient_entity_action` (`recipient_user_id`,`module`,`entity_id`,`entity_ref`,`action_type`),
  KEY `recipient_vendor_id` (`recipient_vendor_id`),
  KEY `ix_user_pending_actions_recipient_active` (`recipient_user_id`,`is_active`),
  KEY `ix_user_pending_actions_module_entity` (`module`,`entity_id`),
  CONSTRAINT `user_pending_actions_ibfk_1` FOREIGN KEY (`recipient_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `user_pending_actions_ibfk_2` FOREIGN KEY (`recipient_vendor_id`) REFERENCES `vendors` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=193 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_pending_actions`
--

LOCK TABLES `user_pending_actions` WRITE;
/*!40000 ALTER TABLE `user_pending_actions` DISABLE KEYS */;
INSERT INTO `user_pending_actions` VALUES (3,11,NULL,'services',4,'','legacy_customer_document_uploaded','Customer documents received','Customer uploaded Purchase Order for SRV_1788162694429.','Open service','/services/4','Notification','2026-08-31 07:53:55',0,0,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:02','2026-09-05 08:13:03'),(4,1,NULL,'services',5,'','legacy_customer_document_uploaded','Customer documents received','Customer uploaded Purchase Order for SRV_1788163516751.','Open service','/services/5','Notification','2026-08-31 08:06:40',0,0,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03','2026-09-05 08:13:03'),(5,11,NULL,'services',5,'','legacy_customer_document_uploaded','Customer documents received','Customer uploaded Purchase Order for SRV_1788163516751.','Open service','/services/5','Notification','2026-08-31 08:06:40',0,0,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03','2026-09-05 08:13:03'),(6,11,NULL,'services',6,'','legacy_customer_document_uploaded','Customer documents received','Customer uploaded Purchase Order for SRV_1788232354020.','Open service','/services/6','Notification','2026-09-01 03:19:16',0,0,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03','2026-09-05 08:13:03'),(7,11,NULL,'services',8,'','legacy_customer_document_uploaded','Customer documents received','Customer uploaded Purchase Order for SRV_1788494569138.','Open service','/services/8','Notification','2026-09-04 04:41:27',0,0,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03','2026-09-05 08:13:03'),(8,1,NULL,'complaints',2,'','triage_complaint','Complaint COMP-2026-0002','Complaint is Pending. Review and take action.','Open complaint','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(9,5,NULL,'complaints',2,'','triage_complaint','Complaint COMP-2026-0002','Complaint is Pending. Review and take action.','Open complaint','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(10,8,NULL,'complaints',2,'','triage_complaint','Complaint COMP-2026-0002','Complaint is Pending. Review and take action.','Open complaint','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(11,11,NULL,'complaints',2,'','triage_complaint','Complaint COMP-2026-0002','Complaint is Pending. Review and take action.','Open complaint','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(12,1,NULL,'complaints',2,'','request_documents','Complaint COMP-2026-0002','Customer documents have not been requested yet.','Request documents','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(13,5,NULL,'complaints',2,'','request_documents','Complaint COMP-2026-0002','Customer documents have not been requested yet.','Request documents','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(14,8,NULL,'complaints',2,'','request_documents','Complaint COMP-2026-0002','Customer documents have not been requested yet.','Request documents','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(15,11,NULL,'complaints',2,'','request_documents','Complaint COMP-2026-0002','Customer documents have not been requested yet.','Request documents','/complaints/2','Pending','2026-08-10 11:00:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(16,1,NULL,'complaints',3,'','triage_complaint','Complaint IDC_1787236280959','Complaint is Pending. Review and take action.','Open complaint','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(17,5,NULL,'complaints',3,'','triage_complaint','Complaint IDC_1787236280959','Complaint is Pending. Review and take action.','Open complaint','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(18,8,NULL,'complaints',3,'','triage_complaint','Complaint IDC_1787236280959','Complaint is Pending. Review and take action.','Open complaint','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(19,11,NULL,'complaints',3,'','triage_complaint','Complaint IDC_1787236280959','Complaint is Pending. Review and take action.','Open complaint','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(20,1,NULL,'complaints',3,'','request_documents','Complaint IDC_1787236280959','Customer documents have not been requested yet.','Request documents','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(21,5,NULL,'complaints',3,'','request_documents','Complaint IDC_1787236280959','Customer documents have not been requested yet.','Request documents','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(22,8,NULL,'complaints',3,'','request_documents','Complaint IDC_1787236280959','Customer documents have not been requested yet.','Request documents','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(23,11,NULL,'complaints',3,'','request_documents','Complaint IDC_1787236280959','Customer documents have not been requested yet.','Request documents','/complaints/3','Pending','2026-08-20 14:31:20',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(24,1,NULL,'complaints',4,'','triage_complaint','Complaint IDC_1787236295330','Complaint is Pending. Review and take action.','Open complaint','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(25,5,NULL,'complaints',4,'','triage_complaint','Complaint IDC_1787236295330','Complaint is Pending. Review and take action.','Open complaint','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(26,8,NULL,'complaints',4,'','triage_complaint','Complaint IDC_1787236295330','Complaint is Pending. Review and take action.','Open complaint','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(27,11,NULL,'complaints',4,'','triage_complaint','Complaint IDC_1787236295330','Complaint is Pending. Review and take action.','Open complaint','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(28,1,NULL,'complaints',4,'','request_documents','Complaint IDC_1787236295330','Customer documents have not been requested yet.','Request documents','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(29,5,NULL,'complaints',4,'','request_documents','Complaint IDC_1787236295330','Customer documents have not been requested yet.','Request documents','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(30,8,NULL,'complaints',4,'','request_documents','Complaint IDC_1787236295330','Customer documents have not been requested yet.','Request documents','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(31,11,NULL,'complaints',4,'','request_documents','Complaint IDC_1787236295330','Customer documents have not been requested yet.','Request documents','/complaints/4','Pending','2026-08-20 14:31:35',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(32,1,NULL,'complaints',5,'','triage_complaint','Complaint IDC_1787408167976','Complaint is Pending. Review and take action.','Open complaint','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(33,5,NULL,'complaints',5,'','triage_complaint','Complaint IDC_1787408167976','Complaint is Pending. Review and take action.','Open complaint','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(34,8,NULL,'complaints',5,'','triage_complaint','Complaint IDC_1787408167976','Complaint is Pending. Review and take action.','Open complaint','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(35,11,NULL,'complaints',5,'','triage_complaint','Complaint IDC_1787408167976','Complaint is Pending. Review and take action.','Open complaint','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(36,1,NULL,'complaints',5,'','request_documents','Complaint IDC_1787408167976','Customer documents have not been requested yet.','Request documents','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(37,5,NULL,'complaints',5,'','request_documents','Complaint IDC_1787408167976','Customer documents have not been requested yet.','Request documents','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(38,8,NULL,'complaints',5,'','request_documents','Complaint IDC_1787408167976','Customer documents have not been requested yet.','Request documents','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(39,11,NULL,'complaints',5,'','request_documents','Complaint IDC_1787408167976','Customer documents have not been requested yet.','Request documents','/complaints/5','Pending','2026-08-22 14:16:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(40,1,NULL,'complaints',6,'','triage_complaint','Complaint IDC_1787467506528','Complaint is In Process. Review and take action.','Open complaint','/complaints/6','In Process','2026-08-23 06:48:44',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(41,5,NULL,'complaints',6,'','triage_complaint','Complaint IDC_1787467506528','Complaint is In Process. Review and take action.','Open complaint','/complaints/6','In Process','2026-08-23 06:48:44',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(42,8,NULL,'complaints',6,'','triage_complaint','Complaint IDC_1787467506528','Complaint is In Process. Review and take action.','Open complaint','/complaints/6','In Process','2026-08-23 06:48:44',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(43,11,NULL,'complaints',6,'','triage_complaint','Complaint IDC_1787467506528','Complaint is In Process. Review and take action.','Open complaint','/complaints/6','In Process','2026-08-23 06:48:44',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(44,2,NULL,'complaints',6,'','work_complaint','Complaint IDC_1787467506528','Assigned complaint is In Process.','Open complaint','/complaints/6','In Process','2026-08-23 06:48:44',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(45,1,NULL,'complaints',7,'','triage_complaint','Complaint IDC_1787472834954','Complaint is Pending. Review and take action.','Open complaint','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(46,5,NULL,'complaints',7,'','triage_complaint','Complaint IDC_1787472834954','Complaint is Pending. Review and take action.','Open complaint','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(47,8,NULL,'complaints',7,'','triage_complaint','Complaint IDC_1787472834954','Complaint is Pending. Review and take action.','Open complaint','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(48,11,NULL,'complaints',7,'','triage_complaint','Complaint IDC_1787472834954','Complaint is Pending. Review and take action.','Open complaint','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(49,1,NULL,'complaints',7,'','request_documents','Complaint IDC_1787472834954','Customer documents have not been requested yet.','Request documents','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(50,5,NULL,'complaints',7,'','request_documents','Complaint IDC_1787472834954','Customer documents have not been requested yet.','Request documents','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(51,8,NULL,'complaints',7,'','request_documents','Complaint IDC_1787472834954','Customer documents have not been requested yet.','Request documents','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(52,11,NULL,'complaints',7,'','request_documents','Complaint IDC_1787472834954','Customer documents have not been requested yet.','Request documents','/complaints/7','Pending','2026-08-23 08:13:54',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(53,1,NULL,'complaints',8,'','triage_complaint','Complaint IDC_1787480884086','Complaint is Pending. Review and take action.','Open complaint','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(54,5,NULL,'complaints',8,'','triage_complaint','Complaint IDC_1787480884086','Complaint is Pending. Review and take action.','Open complaint','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(55,8,NULL,'complaints',8,'','triage_complaint','Complaint IDC_1787480884086','Complaint is Pending. Review and take action.','Open complaint','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(56,11,NULL,'complaints',8,'','triage_complaint','Complaint IDC_1787480884086','Complaint is Pending. Review and take action.','Open complaint','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(57,1,NULL,'complaints',8,'','request_documents','Complaint IDC_1787480884086','Customer documents have not been requested yet.','Request documents','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(58,5,NULL,'complaints',8,'','request_documents','Complaint IDC_1787480884086','Customer documents have not been requested yet.','Request documents','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(59,8,NULL,'complaints',8,'','request_documents','Complaint IDC_1787480884086','Customer documents have not been requested yet.','Request documents','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(60,11,NULL,'complaints',8,'','request_documents','Complaint IDC_1787480884086','Customer documents have not been requested yet.','Request documents','/complaints/8','Pending','2026-08-23 10:28:04',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(61,1,NULL,'complaints',9,'','triage_complaint','Complaint IDC_SEED_1788007011190','Complaint is Pending. Review and take action.','Open complaint','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(62,5,NULL,'complaints',9,'','triage_complaint','Complaint IDC_SEED_1788007011190','Complaint is Pending. Review and take action.','Open complaint','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(63,8,NULL,'complaints',9,'','triage_complaint','Complaint IDC_SEED_1788007011190','Complaint is Pending. Review and take action.','Open complaint','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(64,11,NULL,'complaints',9,'','triage_complaint','Complaint IDC_SEED_1788007011190','Complaint is Pending. Review and take action.','Open complaint','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(65,1,NULL,'complaints',9,'','request_documents','Complaint IDC_SEED_1788007011190','Customer documents have not been requested yet.','Request documents','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(66,5,NULL,'complaints',9,'','request_documents','Complaint IDC_SEED_1788007011190','Customer documents have not been requested yet.','Request documents','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(67,8,NULL,'complaints',9,'','request_documents','Complaint IDC_SEED_1788007011190','Customer documents have not been requested yet.','Request documents','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(68,11,NULL,'complaints',9,'','request_documents','Complaint IDC_SEED_1788007011190','Customer documents have not been requested yet.','Request documents','/complaints/9','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(69,1,NULL,'complaints',10,'','triage_complaint','Complaint IDC_SEED_1788007011191','Complaint is In Process. Review and take action.','Open complaint','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(70,5,NULL,'complaints',10,'','triage_complaint','Complaint IDC_SEED_1788007011191','Complaint is In Process. Review and take action.','Open complaint','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(71,8,NULL,'complaints',10,'','triage_complaint','Complaint IDC_SEED_1788007011191','Complaint is In Process. Review and take action.','Open complaint','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(72,11,NULL,'complaints',10,'','triage_complaint','Complaint IDC_SEED_1788007011191','Complaint is In Process. Review and take action.','Open complaint','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(73,1,NULL,'complaints',10,'','request_documents','Complaint IDC_SEED_1788007011191','Customer documents have not been requested yet.','Request documents','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(74,5,NULL,'complaints',10,'','request_documents','Complaint IDC_SEED_1788007011191','Customer documents have not been requested yet.','Request documents','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(75,8,NULL,'complaints',10,'','request_documents','Complaint IDC_SEED_1788007011191','Customer documents have not been requested yet.','Request documents','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(76,11,NULL,'complaints',10,'','request_documents','Complaint IDC_SEED_1788007011191','Customer documents have not been requested yet.','Request documents','/complaints/10','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(77,1,NULL,'complaints',11,'','triage_complaint','Complaint IDC_SEED_1788007011192','Complaint is Pending. Review and take action.','Open complaint','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(78,5,NULL,'complaints',11,'','triage_complaint','Complaint IDC_SEED_1788007011192','Complaint is Pending. Review and take action.','Open complaint','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(79,6,NULL,'complaints',11,'','triage_complaint','Complaint IDC_SEED_1788007011192','Complaint is Pending. Review and take action.','Open complaint','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(80,8,NULL,'complaints',11,'','triage_complaint','Complaint IDC_SEED_1788007011192','Complaint is Pending. Review and take action.','Open complaint','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(81,11,NULL,'complaints',11,'','triage_complaint','Complaint IDC_SEED_1788007011192','Complaint is Pending. Review and take action.','Open complaint','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(82,1,NULL,'complaints',11,'','request_documents','Complaint IDC_SEED_1788007011192','Customer documents have not been requested yet.','Request documents','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(83,5,NULL,'complaints',11,'','request_documents','Complaint IDC_SEED_1788007011192','Customer documents have not been requested yet.','Request documents','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(84,6,NULL,'complaints',11,'','request_documents','Complaint IDC_SEED_1788007011192','Customer documents have not been requested yet.','Request documents','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(85,8,NULL,'complaints',11,'','request_documents','Complaint IDC_SEED_1788007011192','Customer documents have not been requested yet.','Request documents','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(86,11,NULL,'complaints',11,'','request_documents','Complaint IDC_SEED_1788007011192','Customer documents have not been requested yet.','Request documents','/complaints/11','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(87,1,NULL,'complaints',12,'','triage_complaint','Complaint IDC_SEED_1788007011193','Complaint is Pending. Review and take action.','Open complaint','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(88,5,NULL,'complaints',12,'','triage_complaint','Complaint IDC_SEED_1788007011193','Complaint is Pending. Review and take action.','Open complaint','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(89,8,NULL,'complaints',12,'','triage_complaint','Complaint IDC_SEED_1788007011193','Complaint is Pending. Review and take action.','Open complaint','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(90,11,NULL,'complaints',12,'','triage_complaint','Complaint IDC_SEED_1788007011193','Complaint is Pending. Review and take action.','Open complaint','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(91,1,NULL,'complaints',12,'','request_documents','Complaint IDC_SEED_1788007011193','Customer documents have not been requested yet.','Request documents','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(92,5,NULL,'complaints',12,'','request_documents','Complaint IDC_SEED_1788007011193','Customer documents have not been requested yet.','Request documents','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(93,8,NULL,'complaints',12,'','request_documents','Complaint IDC_SEED_1788007011193','Customer documents have not been requested yet.','Request documents','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(94,11,NULL,'complaints',12,'','request_documents','Complaint IDC_SEED_1788007011193','Customer documents have not been requested yet.','Request documents','/complaints/12','Pending','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(95,1,NULL,'complaints',13,'','triage_complaint','Complaint IDC_SEED_1788007011194','Complaint is In Process. Review and take action.','Open complaint','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(96,5,NULL,'complaints',13,'','triage_complaint','Complaint IDC_SEED_1788007011194','Complaint is In Process. Review and take action.','Open complaint','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(97,8,NULL,'complaints',13,'','triage_complaint','Complaint IDC_SEED_1788007011194','Complaint is In Process. Review and take action.','Open complaint','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(98,11,NULL,'complaints',13,'','triage_complaint','Complaint IDC_SEED_1788007011194','Complaint is In Process. Review and take action.','Open complaint','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(99,1,NULL,'complaints',13,'','request_documents','Complaint IDC_SEED_1788007011194','Customer documents have not been requested yet.','Request documents','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(100,5,NULL,'complaints',13,'','request_documents','Complaint IDC_SEED_1788007011194','Customer documents have not been requested yet.','Request documents','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(101,8,NULL,'complaints',13,'','request_documents','Complaint IDC_SEED_1788007011194','Customer documents have not been requested yet.','Request documents','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(102,11,NULL,'complaints',13,'','request_documents','Complaint IDC_SEED_1788007011194','Customer documents have not been requested yet.','Request documents','/complaints/13','In Process','2026-08-29 12:36:51',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(103,1,NULL,'complaints',17,'','triage_complaint','Complaint IDC_1788105640261','Complaint is Pending. Review and take action.','Open complaint','/complaints/17','Pending','2026-08-30 16:00:40',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(104,5,NULL,'complaints',17,'','triage_complaint','Complaint IDC_1788105640261','Complaint is Pending. Review and take action.','Open complaint','/complaints/17','Pending','2026-08-30 16:00:40',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(105,8,NULL,'complaints',17,'','triage_complaint','Complaint IDC_1788105640261','Complaint is Pending. Review and take action.','Open complaint','/complaints/17','Pending','2026-08-30 16:00:40',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(106,11,NULL,'complaints',17,'','triage_complaint','Complaint IDC_1788105640261','Complaint is Pending. Review and take action.','Open complaint','/complaints/17','Pending','2026-08-30 16:00:40',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(107,1,NULL,'complaints',17,'','request_documents','Complaint IDC_1788105640261','Customer documents have not been requested yet.','Request documents','/complaints/17','Pending','2026-08-30 16:00:40',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(108,5,NULL,'complaints',17,'','request_documents','Complaint IDC_1788105640261','Customer documents have not been requested yet.','Request documents','/complaints/17','Pending','2026-08-30 16:00:40',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(109,8,NULL,'complaints',17,'','request_documents','Complaint IDC_1788105640261','Customer documents have not been requested yet.','Request documents','/complaints/17','Pending','2026-08-30 16:00:40',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(110,11,NULL,'complaints',17,'','request_documents','Complaint IDC_1788105640261','Customer documents have not been requested yet.','Request documents','/complaints/17','Pending','2026-08-30 16:00:40',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(111,1,NULL,'complaints',18,'','triage_complaint','Complaint IDC_1788162694425','Complaint is Pending. Review and take action.','Open complaint','/complaints/18','Pending','2026-08-31 07:51:34',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(112,5,NULL,'complaints',18,'','triage_complaint','Complaint IDC_1788162694425','Complaint is Pending. Review and take action.','Open complaint','/complaints/18','Pending','2026-08-31 07:51:34',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(113,8,NULL,'complaints',18,'','triage_complaint','Complaint IDC_1788162694425','Complaint is Pending. Review and take action.','Open complaint','/complaints/18','Pending','2026-08-31 07:51:34',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(114,11,NULL,'complaints',18,'','triage_complaint','Complaint IDC_1788162694425','Complaint is Pending. Review and take action.','Open complaint','/complaints/18','Pending','2026-08-31 07:51:34',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(115,1,NULL,'complaints',19,'','triage_complaint','Complaint IDC_1788163516750','Complaint is Pending. Review and take action.','Open complaint','/complaints/19','Pending','2026-08-31 08:05:17',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(116,5,NULL,'complaints',19,'','triage_complaint','Complaint IDC_1788163516750','Complaint is Pending. Review and take action.','Open complaint','/complaints/19','Pending','2026-08-31 08:05:17',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(117,8,NULL,'complaints',19,'','triage_complaint','Complaint IDC_1788163516750','Complaint is Pending. Review and take action.','Open complaint','/complaints/19','Pending','2026-08-31 08:05:17',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(118,11,NULL,'complaints',19,'','triage_complaint','Complaint IDC_1788163516750','Complaint is Pending. Review and take action.','Open complaint','/complaints/19','Pending','2026-08-31 08:05:17',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(119,1,NULL,'complaints',20,'','triage_complaint','Complaint IDC_1788232354014','Complaint is Pending. Review and take action.','Open complaint','/complaints/20','Pending','2026-09-01 03:12:34',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(120,5,NULL,'complaints',20,'','triage_complaint','Complaint IDC_1788232354014','Complaint is Pending. Review and take action.','Open complaint','/complaints/20','Pending','2026-09-01 03:12:34',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(121,8,NULL,'complaints',20,'','triage_complaint','Complaint IDC_1788232354014','Complaint is Pending. Review and take action.','Open complaint','/complaints/20','Pending','2026-09-01 03:12:34',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(122,11,NULL,'complaints',20,'','triage_complaint','Complaint IDC_1788232354014','Complaint is Pending. Review and take action.','Open complaint','/complaints/20','Pending','2026-09-01 03:12:34',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(123,1,NULL,'complaints',21,'','triage_complaint','Complaint IDC_1788493375170','Complaint is Pending. Review and take action.','Open complaint','/complaints/21','Pending','2026-09-04 03:42:55',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(124,5,NULL,'complaints',21,'','triage_complaint','Complaint IDC_1788493375170','Complaint is Pending. Review and take action.','Open complaint','/complaints/21','Pending','2026-09-04 03:42:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(125,8,NULL,'complaints',21,'','triage_complaint','Complaint IDC_1788493375170','Complaint is Pending. Review and take action.','Open complaint','/complaints/21','Pending','2026-09-04 03:42:55',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(126,11,NULL,'complaints',21,'','triage_complaint','Complaint IDC_1788493375170','Complaint is Pending. Review and take action.','Open complaint','/complaints/21','Pending','2026-09-04 03:42:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(127,1,NULL,'complaints',21,'','request_documents','Complaint IDC_1788493375170','Customer documents have not been requested yet.','Request documents','/complaints/21','Pending','2026-09-04 03:42:55',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(128,5,NULL,'complaints',21,'','request_documents','Complaint IDC_1788493375170','Customer documents have not been requested yet.','Request documents','/complaints/21','Pending','2026-09-04 03:42:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(129,8,NULL,'complaints',21,'','request_documents','Complaint IDC_1788493375170','Customer documents have not been requested yet.','Request documents','/complaints/21','Pending','2026-09-04 03:42:55',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(130,11,NULL,'complaints',21,'','request_documents','Complaint IDC_1788493375170','Customer documents have not been requested yet.','Request documents','/complaints/21','Pending','2026-09-04 03:42:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(131,1,NULL,'complaints',22,'','triage_complaint','Complaint IDC_1788494569135','Complaint is Pending. Review and take action.','Open complaint','/complaints/22','Pending','2026-09-04 04:02:49',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(132,5,NULL,'complaints',22,'','triage_complaint','Complaint IDC_1788494569135','Complaint is Pending. Review and take action.','Open complaint','/complaints/22','Pending','2026-09-04 04:02:49',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(133,8,NULL,'complaints',22,'','triage_complaint','Complaint IDC_1788494569135','Complaint is Pending. Review and take action.','Open complaint','/complaints/22','Pending','2026-09-04 04:02:49',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(134,11,NULL,'complaints',22,'','triage_complaint','Complaint IDC_1788494569135','Complaint is Pending. Review and take action.','Open complaint','/complaints/22','Pending','2026-09-04 04:02:49',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(135,1,NULL,'complaints',22,'','request_documents','Complaint IDC_1788494569135','Customer documents have not been requested yet.','Request documents','/complaints/22','Pending','2026-09-04 04:02:49',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(136,5,NULL,'complaints',22,'','request_documents','Complaint IDC_1788494569135','Customer documents have not been requested yet.','Request documents','/complaints/22','Pending','2026-09-04 04:02:49',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(137,8,NULL,'complaints',22,'','request_documents','Complaint IDC_1788494569135','Customer documents have not been requested yet.','Request documents','/complaints/22','Pending','2026-09-04 04:02:49',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(138,11,NULL,'complaints',22,'','request_documents','Complaint IDC_1788494569135','Customer documents have not been requested yet.','Request documents','/complaints/22','Pending','2026-09-04 04:02:49',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(139,1,NULL,'complaints',23,'','triage_complaint','Complaint IDC_1788581772752','Complaint is Pending. Review and take action.','Open complaint','/complaints/23','Pending','2026-09-05 04:16:13',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(140,5,NULL,'complaints',23,'','triage_complaint','Complaint IDC_1788581772752','Complaint is Pending. Review and take action.','Open complaint','/complaints/23','Pending','2026-09-05 04:16:13',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(141,8,NULL,'complaints',23,'','triage_complaint','Complaint IDC_1788581772752','Complaint is Pending. Review and take action.','Open complaint','/complaints/23','Pending','2026-09-05 04:16:13',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(142,11,NULL,'complaints',23,'','triage_complaint','Complaint IDC_1788581772752','Complaint is Pending. Review and take action.','Open complaint','/complaints/23','Pending','2026-09-05 04:16:13',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(143,1,NULL,'complaints',23,'','request_documents','Complaint IDC_1788581772752','Customer documents have not been requested yet.','Request documents','/complaints/23','Pending','2026-09-05 04:16:13',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(144,5,NULL,'complaints',23,'','request_documents','Complaint IDC_1788581772752','Customer documents have not been requested yet.','Request documents','/complaints/23','Pending','2026-09-05 04:16:13',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(145,8,NULL,'complaints',23,'','request_documents','Complaint IDC_1788581772752','Customer documents have not been requested yet.','Request documents','/complaints/23','Pending','2026-09-05 04:16:13',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(146,11,NULL,'complaints',23,'','request_documents','Complaint IDC_1788581772752','Customer documents have not been requested yet.','Request documents','/complaints/23','Pending','2026-09-05 04:16:13',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(147,1,NULL,'complaints',24,'','triage_complaint','Complaint IDC_1788581931214','Complaint is Pending. Review and take action.','Open complaint','/complaints/24','Pending','2026-09-05 05:54:53',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(148,5,NULL,'complaints',24,'','triage_complaint','Complaint IDC_1788581931214','Complaint is Pending. Review and take action.','Open complaint','/complaints/24','Pending','2026-09-05 05:54:53',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(149,8,NULL,'complaints',24,'','triage_complaint','Complaint IDC_1788581931214','Complaint is Pending. Review and take action.','Open complaint','/complaints/24','Pending','2026-09-05 05:54:53',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(150,11,NULL,'complaints',24,'','triage_complaint','Complaint IDC_1788581931214','Complaint is Pending. Review and take action.','Open complaint','/complaints/24','Pending','2026-09-05 05:54:53',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(151,2,NULL,'installations',2,'','complete_installation','Installation #2','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/2?edit=1','Assigned','2026-08-20 07:32:21',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(152,1,NULL,'installations',3,'','approve_payment','Installation #3','Engineer raised a payment request.','Approve payment','/installations/3?edit=1','Payment Pending','2026-08-10 17:10:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(153,8,NULL,'installations',3,'','approve_payment','Installation #3','Engineer raised a payment request.','Approve payment','/installations/3?edit=1','Payment Pending','2026-08-10 17:10:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(154,11,NULL,'installations',3,'','approve_payment','Installation #3','Engineer raised a payment request.','Approve payment','/installations/3?edit=1','Payment Pending','2026-08-10 17:10:00',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(155,10,NULL,'installations',12,'','complete_installation','Installation #12','Installation is In Progress. Complete work and submit proof.','Complete installation','/installations/12?edit=1','In Progress','2026-08-30 12:58:16',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(156,2,NULL,'installations',13,'','complete_installation','Installation #13','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/13?edit=1','Assigned','2026-08-30 12:58:16',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(157,10,NULL,'installations',15,'','complete_installation','Installation #15','Installation is In Progress. Complete work and submit proof.','Complete installation','/installations/15?edit=1','In Progress','2026-08-30 12:58:16',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(158,2,NULL,'installations',16,'','complete_installation','Installation #16','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/16?edit=1','Assigned','2026-08-30 12:58:16',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(159,10,NULL,'installations',18,'','complete_installation','Installation #18','Installation is In Progress. Complete work and submit proof.','Complete installation','/installations/18?edit=1','In Progress','2026-08-30 12:58:16',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(160,2,NULL,'installations',19,'','complete_installation','Installation #19','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/19?edit=1','Assigned','2026-08-30 14:09:56',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(161,9,NULL,'installations',19,'','assign_engineer','Installation #19','Assign an engineer for this installation.','Assign engineer','/installations/19?edit=1','Assigned','2026-08-30 14:09:56',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(162,2,NULL,'installations',20,'','complete_installation','Installation #20','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/20?edit=1','Assigned','2026-08-30 14:09:56',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(163,9,NULL,'installations',20,'','assign_engineer','Installation #20','Assign an engineer for this installation.','Assign engineer','/installations/20?edit=1','Assigned','2026-08-30 14:09:56',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(164,9,NULL,'installations',21,'','assign_engineer','Installation #21','Assign an engineer for this installation.','Assign engineer','/installations/21?edit=1','Submitted','2026-08-30 14:10:01',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(165,2,NULL,'installations',22,'','complete_installation','Installation #22','Installation is In Progress. Complete work and submit proof.','Complete installation','/installations/22?edit=1','In Progress','2026-08-31 07:28:32',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(166,3,NULL,'installations',24,'','complete_installation','Installation #24','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/24?edit=1','Assigned','2026-08-31 07:29:21',1,1,'2026-09-05 08:17:46',NULL,'2026-09-05 08:13:03','2026-09-05 08:17:46'),(167,4,NULL,'installations',24,'','assign_engineer','Installation #24','Assign an engineer for this installation.','Assign engineer','/installations/24?edit=1','Assigned','2026-08-31 07:29:21',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(168,2,NULL,'installations',27,'','complete_installation','Installation #27','Installation is Assigned. Complete work and submit proof.','Complete installation','/installations/27?edit=1','Assigned','2026-09-05 04:53:18',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(169,1,NULL,'installations',28,'','approve_payment','Installation #28','Engineer raised a payment request.','Approve payment','/installations/28?edit=1','Payment Pending','2026-09-04 13:12:55',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(170,8,NULL,'installations',28,'','approve_payment','Installation #28','Engineer raised a payment request.','Approve payment','/installations/28?edit=1','Payment Pending','2026-09-04 13:12:55',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(171,11,NULL,'installations',28,'','approve_payment','Installation #28','Engineer raised a payment request.','Approve payment','/installations/28?edit=1','Payment Pending','2026-09-04 13:12:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(172,3,NULL,'installations',29,'','raise_payment','Installation #29','Admin approved completion. Raise payment request.','Raise payment','/installations/29?edit=1','Installation Completed','2026-09-05 07:22:16',1,1,'2026-09-05 08:17:46',NULL,'2026-09-05 08:13:03','2026-09-05 08:17:46'),(173,2,NULL,'services',1,'','complete_service','Service SRV_1787467506532','Service is Assigned. Continue engineer workflow.','Open service','/services/1','Assigned','2026-08-23 07:56:07',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(174,1,NULL,'services',2,'','assign_service','Service SRV_1787472834960','Service request is unassigned.','Assign service','/services/2','Service Team Review','2026-08-23 08:13:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(175,8,NULL,'services',2,'','assign_service','Service SRV_1787472834960','Service request is unassigned.','Assign service','/services/2','Service Team Review','2026-08-23 08:13:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(176,11,NULL,'services',2,'','assign_service','Service SRV_1787472834960','Service request is unassigned.','Assign service','/services/2','Service Team Review','2026-08-23 08:13:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(177,1,NULL,'services',4,'','assign_service','Service SRV_1788162694429','Service request is unassigned.','Assign service','/services/4','Service Team Review','2026-08-31 08:01:46',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(178,8,NULL,'services',4,'','assign_service','Service SRV_1788162694429','Service request is unassigned.','Assign service','/services/4','Service Team Review','2026-08-31 08:01:46',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(179,11,NULL,'services',4,'','assign_service','Service SRV_1788162694429','Service request is unassigned.','Assign service','/services/4','Service Team Review','2026-08-31 08:01:46',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(180,1,NULL,'services',7,'','assign_service','Service SRV_1788493375179','Service request is unassigned.','Assign service','/services/7','Service Team Review','2026-09-04 03:42:55',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(181,8,NULL,'services',7,'','assign_service','Service SRV_1788493375179','Service request is unassigned.','Assign service','/services/7','Service Team Review','2026-09-04 03:42:55',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(182,11,NULL,'services',7,'','assign_service','Service SRV_1788493375179','Service request is unassigned.','Assign service','/services/7','Service Team Review','2026-09-04 03:42:55',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(183,1,NULL,'services',9,'','assign_service','Service SRV_1788581772757','Service request is unassigned.','Assign service','/services/9','Service Team Review','2026-09-05 04:16:13',1,1,'2026-09-05 17:01:19',NULL,'2026-09-05 08:13:03','2026-09-05 17:01:19'),(184,8,NULL,'services',9,'','assign_service','Service SRV_1788581772757','Service request is unassigned.','Assign service','/services/9','Service Team Review','2026-09-05 04:16:13',1,1,'2026-09-05 08:18:10',NULL,'2026-09-05 08:13:03','2026-09-05 08:18:10'),(185,11,NULL,'services',9,'','assign_service','Service SRV_1788581772757','Service request is unassigned.','Assign service','/services/9','Service Team Review','2026-09-05 04:16:13',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(186,4,NULL,'orders',7,'','update_shipment','Order V1-ORD-002','Order is In Transit. Update shipment details.','Update shipment','/orders/7','In Transit','2026-08-29 12:36:52',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(187,4,NULL,'orders',8,'','fulfill_order','Order V1-ORD-003','Order is pending fulfillment.','Fulfill order','/orders/8','Pending','2026-08-29 12:36:52',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(188,4,NULL,'orders',24,'','fulfill_order','Order GEMC-511TEST','Order is pending fulfillment.','Fulfill order','/orders/24','Pending','2026-08-31 07:05:01',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(189,9,NULL,'orders',27,'','fulfill_order','Order TESTqeorhjq9','Order is pending fulfillment.','Fulfill order','/orders/27','Pending','2026-09-05 06:05:23',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(190,1,NULL,'claims',2,'','process_claim','Claim CLM-2026-0002','Claim is awaiting processing.','Process claim','/claims/2','Processing','2026-08-20 07:32:21',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(191,8,NULL,'claims',2,'','process_claim','Claim CLM-2026-0002','Claim is awaiting processing.','Process claim','/claims/2','Processing','2026-08-20 07:32:21',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03'),(192,11,NULL,'claims',2,'','process_claim','Claim CLM-2026-0002','Claim is awaiting processing.','Process claim','/claims/2','Processing','2026-08-20 07:32:21',1,0,NULL,NULL,'2026-09-05 08:13:03','2026-09-05 08:13:03');
/*!40000 ALTER TABLE `user_pending_actions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Administrator','admin@indcool.com','$2b$12$mYDlxvUr6Fvk8BypIcw1euN6Uk7.tPx62mFVEE.DKSVBufuSpeSf2','admin','9999999991',1,'2026-08-20 07:32:21','2026-08-29 12:36:51',NULL),(2,'Ravi Kumar','ravi@indcool.com','$2b$12$D3Pxroi9UU2FTkC4kVohvOm2486T1xYmpufu0vuSUGQXu7JIhUqK2','engineer','9810000001',1,'2026-08-20 07:32:21','2026-08-30 10:05:40',NULL),(3,'Sunita Patel','sunita@indcool.com','$2b$12$54DpuGkjoYhXNBLODIhXzuyUZY2VlVlU9gJ86.BBMPRxJxuM4Fco2','engineer','9810000002',1,'2026-08-20 07:32:21','2026-08-31 09:16:19',NULL),(4,'Vendor One User','vendor1@indcool.com','$2b$12$1mBhNp4LN11vemuWxV6vVe31iWMski7QaXvA6.rbdZu0kQxMjlPjS','vendor','9820000001',1,'2026-08-20 07:32:21','2026-08-31 08:15:40',NULL),(5,'Call Center User','callcenter@indcool.com','$2b$12$7YR9LYrM/0jU6KP3wF9F7O3vtQoxMTX5VhKKvNto6QrmLb2CBlz32','callcenter','9830000001',1,'2026-08-20 07:32:21','2026-08-31 08:03:53',NULL),(6,'Sales User','sales@indcool.com','$2b$12$SqNeXIrENHB7mAdMe8aoD./4sM.f7XgXd4DevKOrXExOHL9PDHgvS','sales','9840000001',1,'2026-08-20 07:32:21','2026-08-20 07:32:21',NULL),(7,'vendor2','vendor2@indcool.com','$2b$12$/BOxefjZ3tK92Ek8u.Tz7.Q0KLph39OjXnQ5vcldLd4OofN6qkaD.','vendor',NULL,1,'2026-08-23 01:41:26','2026-08-30 13:30:07',NULL),(8,'VISWESH MISHRA','vishwesh@indcool.in','$2b$12$B.ToTlUxsRtp27aZP/V6WeE9DfkLnuCEjGHSR45nFzd.PnIxftlBC','service','9970093899',1,'2026-08-23 06:42:10','2026-08-23 06:42:10',NULL),(9,'IEPL','ieplvendor@indcool.com','$2b$12$FBWMF3yUxe9ssJz/1r.Zf.X0Osw35x8Aqi4IihIEy.EL1wE4Vx716','vendor','7011249661',1,'2026-08-23 10:36:34','2026-08-30 13:41:23',NULL),(10,'Arjun Sharma','arjun@indcool.com','$2b$12$TQiqvbavCzxw5y.HIlbHI.CpUrs2O8gSXPdwB9WraV7khHmcuhHOe','engineer','9810000003',1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(11,'Rohit Verma','service@indcool.com','$2b$12$yCgtmjxJH62fOJ0Oju0Rd.i7NvgdPpeMwh2C7y3hCzNCwiVB105im','indcool_service','9810020202',1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL),(12,'COMTECH ENTERPRISESPVTLTD','cepl@indcool.in','$2b$12$U8iOVVeUdkNpZ2C5kgdxaeE9Tcn8S2098eZQRU0x1Re/CcN55G1YS','vendor','7011249661',1,'2026-09-06 06:11:24','2026-09-06 06:11:24',NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vendors`
--

DROP TABLE IF EXISTS `vendors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vendors` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vendor_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name_of_firm` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gst_no` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address` text COLLATE utf8mb4_unicode_ci,
  `state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `district` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pincode` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latitude` decimal(10,8) DEFAULT NULL,
  `longitude` decimal(11,8) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted_at` datetime DEFAULT NULL,
  `vendor_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vendors`
--

LOCK TABLES `vendors` WRITE;
/*!40000 ALTER TABLE `vendors` DISABLE KEYS */;
INSERT INTO `vendors` VALUES (1,'VEND001','Vendor One Pvt Ltd','Rajesh Verma','9100000001','vendor1@test.com','27ABCDE1234F1Z5','Sector 21, Noida','Uttar Pradesh','Gautam Buddha Nagar','201301',28.53550000,77.39100000,1,'2026-08-20 07:32:21','2026-08-20 07:32:21',NULL,NULL),(2,'VEND002','Vendor Two Appliances','Pooja Mehra','9100000002','vendor2@test.com','07ABCDE1234F1Z5','Rohini, Delhi','Delhi','North West','110085',28.73830000,77.08290000,1,'2026-08-20 07:32:21','2026-08-20 07:32:21',NULL,NULL),(3,'VEND003','IEPL','IEPL',NULL,'ieplvendor@indcool.com',NULL,NULL,NULL,NULL,NULL,NULL,NULL,1,'2026-08-23 11:16:30','2026-08-23 11:16:30',NULL,NULL),(4,'VEND-001','Vendor Test Co','Vendor User','9876543200','vendor@indcool.com','27AAPPU1234A1Z0','New Delhi','Delhi','Central Delhi','110001',NULL,NULL,1,'2026-08-29 12:36:51','2026-08-29 12:36:51',NULL,NULL),(5,'VEND-002','Vendor One Pvt Ltd','Vendor One','9876543201','vendor1@indcool.com','27AAECA1234A1Z5','Gurugram, Haryana','Haryana','Gurugram','122001',NULL,NULL,1,'2026-08-29 12:36:52','2026-08-29 12:36:52',NULL,NULL),(6,'VEND004','cepl','Dhananjai','9891572565','cepl@indcool.in','qwdqwe','swdqsd','Goa','asdas','201308',NULL,NULL,1,'2026-09-06 06:11:24','2026-09-06 06:27:28',NULL,NULL);
/*!40000 ALTER TABLE `vendors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `workflow_tasks`
--

DROP TABLE IF EXISTS `workflow_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workflow_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `task_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `task_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sequence` int NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `advisor_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_data` text COLLATE utf8mb4_unicode_ci,
  `output_data` text COLLATE utf8mb4_unicode_ci,
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `started_at` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `completed_at` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `project_id` (`project_id`),
  CONSTRAINT `workflow_tasks_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `workflow_tasks`
--

LOCK TABLES `workflow_tasks` WRITE;
/*!40000 ALTER TABLE `workflow_tasks` DISABLE KEYS */;
INSERT INTO `workflow_tasks` VALUES (1,1,'Add advisor record','Add Advisor',1,'Completed','ADV-001','{\"name\":\"Advisor One\"}','{\"result\":\"ok\"}',NULL,'2026-08-08T09:00:00Z','2026-08-08T09:03:00Z','2026-08-20 07:32:21','2026-08-20 07:32:21'),(2,1,'Send survey','Send Survey',2,'Running','ADV-001','{\"channel\":\"email\"}',NULL,NULL,'2026-08-08T09:05:00Z',NULL,'2026-08-20 07:32:21','2026-08-20 07:32:21'),(3,2,'Gather responses','Gather Responses',1,'Pending',NULL,NULL,NULL,NULL,NULL,NULL,'2026-08-20 07:32:21','2026-08-20 07:32:21');
/*!40000 ALTER TABLE `workflow_tasks` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-15 18:02:36

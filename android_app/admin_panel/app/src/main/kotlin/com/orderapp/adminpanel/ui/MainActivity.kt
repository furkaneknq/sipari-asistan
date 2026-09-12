package com.orderapp.adminpanel.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.orderapp.adminpanel.data.local.ConfigDataStore
import com.orderapp.adminpanel.ui.calls.IncomingCallsScreen
import com.orderapp.adminpanel.ui.create.CreateOrderScreen
import com.orderapp.adminpanel.ui.customers.CustomerListScreen
import com.orderapp.adminpanel.ui.login.LoginScreen
import com.orderapp.adminpanel.ui.orders.OrderDetailScreen
import com.orderapp.adminpanel.ui.orders.OrdersScreen
import com.orderapp.adminpanel.ui.settings.SettingsScreen
import com.orderapp.adminpanel.ui.theme.AdminPanelTheme
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var configDataStore: ConfigDataStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            AdminPanelTheme {
                var startDestination by remember { mutableStateOf<String?>(null) }

                LaunchedEffect(Unit) {
                    val hasConfig = configDataStore.hasConfig()
                    startDestination = if (hasConfig) "calls" else "login"
                }

                if (startDestination == null) {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                } else {
                    val navController = rememberNavController()
                    val navBackStackEntry by navController.currentBackStackEntryAsState()
                    val currentRoute = navBackStackEntry?.destination?.route

                    val showBottomBar = currentRoute in listOf("calls", "orders", "customers", "settings")

                    Scaffold(
                        bottomBar = {
                            if (showBottomBar) {
                                BottomNavigationBar(navController = navController)
                            }
                        }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = startDestination!!,
                            modifier = Modifier.padding(innerPadding)
                        ) {
                            composable("login") {
                                LoginScreen(
                                    onLoginSuccess = {
                                        navController.navigate("calls") {
                                            popUpTo("login") { inclusive = true }
                                        }
                                    }
                                )
                            }
                            composable("calls") {
                                IncomingCallsScreen(
                                    onNavigateToCreateOrder = { phone ->
                                        navController.navigate("create_order?phone=$phone")
                                    }
                                )
                            }
                            composable("orders") {
                                OrdersScreen(
                                    onNavigateToCreateOrder = { navController.navigate("create_order") },
                                    onNavigateToDetail = { orderId ->
                                        navController.navigate("order_detail/$orderId")
                                    }
                                )
                            }
                            composable(
                                route = "create_order?phone={phone}",
                                arguments = listOf(navArgument("phone") {
                                    type = NavType.StringType
                                    nullable = true
                                    defaultValue = null
                                })
                            ) { backStackEntry ->
                                val phone = backStackEntry.arguments?.getString("phone")
                                CreateOrderScreen(
                                    initialPhone = phone,
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable(
                                route = "order_detail/{orderId}",
                                arguments = listOf(navArgument("orderId") { type = NavType.StringType })
                            ) {
                                OrderDetailScreen(
                                    onBack = { navController.popBackStack() }
                                )
                            }
                            composable("customers") {
                                CustomerListScreen()
                            }
                            composable("settings") {
                                SettingsScreen(
                                    onLoggedOut = {
                                        navController.navigate("login") {
                                            popUpTo(0) { inclusive = true }
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf(
        NavigationItem("calls", "Aramalar", Icons.Default.Call),
        NavigationItem("orders", "Siparişler", Icons.Default.ShoppingCart),
        NavigationItem("customers", "Müşteriler", Icons.Default.Person),
        NavigationItem("settings", "Ayarlar", Icons.Default.Settings)
    )

    NavigationBar {
        val navBackStackEntry by navController.currentBackStackEntryAsState()
        val currentRoute = navBackStackEntry?.destination?.route

        items.forEach { item ->
            NavigationBarItem(
                icon = { Icon(imageVector = item.icon, contentDescription = item.title) },
                label = { Text(text = item.title) },
                selected = currentRoute == item.route,
                onClick = {
                    navController.navigate(item.route) {
                        popUpTo(navController.graph.startDestinationId) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                }
            )
        }
    }
}

data class NavigationItem(val route: String, val title: String, val icon: ImageVector)
